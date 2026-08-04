import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.error import Conflict, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, filters
from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import (
    AuthenticationSettings,
    get_authentication_settings,
)
from freecoinalert_api.db.repositories.telegram import (
    mark_telegram_processed_update_confirmation_sent,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.telegram.client import (
    TelegramBotClient,
    TelegramDeliveryOutcome,
)
from freecoinalert_api.telegram.bot import create_telegram_bot
from freecoinalert_api.telegram.commands import StartCommandKind, parse_start_command
from freecoinalert_api.telegram.linking import telegram_update_linking_service
from freecoinalert_api.telegram.update_cleanup import telegram_update_cleanup

logger = logging.getLogger(__name__)


class TelegramUpdateProcessorConfigurationError(RuntimeError):
    """Safe failure raised when the local Telegram processor cannot start."""


def create_application(settings: AuthenticationSettings) -> Application:
    bot_token = settings.telegram_bot_token

    if not bot_token:
        raise TelegramUpdateProcessorConfigurationError(
            "Telegram update processing is not configured."
        )

    application = (
        Application.builder()
        .bot(create_telegram_bot(settings))
        .concurrent_updates(False)
        .post_init(_run_startup_cleanup)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["telegram_client"] = TelegramBotClient(application.bot)
    application.add_handler(
        CommandHandler(
            "start",
            handle_start,
            filters=filters.ChatType.PRIVATE,
        )
    )
    application.add_error_handler(handle_polling_error)
    return application


async def handle_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    settings = context.application.bot_data["settings"]
    telegram_client = context.application.bot_data["telegram_client"]

    if not isinstance(settings, AuthenticationSettings) or not isinstance(
        telegram_client,
        TelegramBotClient,
    ):
        logger.error("telegram.polling.failed failure_category=application_configuration")
        return

    message = update.effective_message

    if message is None or message.from_user is None:
        return

    logger.info("telegram.update.received update_id=%s", update.update_id)
    command = parse_start_command(update, settings=settings)

    if command is None:
        return

    if command.kind is StartCommandKind.MISSING_TOKEN:
        await telegram_client.send_missing_link_instruction(chat_id=message.chat_id)
        return

    if command.kind is StartCommandKind.INVALID_TOKEN or command.token is None:
        await telegram_client.send_safe_link_failure(
            chat_id=message.chat_id,
            ownership_conflict=False,
        )
        return

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await telegram_update_linking_service.process_link(
            session,
            update_id=update.update_id,
            raw_token=command.token,
            telegram_user_id=message.from_user.id,
            telegram_chat_id=message.chat_id,
            telegram_username=message.from_user.username,
        )

    if result is None:
        return

    if result.should_confirm:
        delivery = await telegram_client.send_link_confirmation(chat_id=message.chat_id)

        if delivery.outcome is TelegramDeliveryOutcome.SENT:
            await _mark_confirmation_sent(update_id=update.update_id)
            logger.info("telegram.confirmation.sent update_id=%s", update.update_id)
        else:
            logger.error(
                "telegram.confirmation.failed update_id=%s failure_category=%s",
                update.update_id,
                delivery.outcome,
            )
        return

    delivery = await telegram_client.send_safe_link_failure(
        chat_id=message.chat_id,
        ownership_conflict=result.outcome == "ownership_conflict",
    )
    logger.info(
        "telegram.link.rejected update_id=%s outcome=%s response_outcome=%s",
        update.update_id,
        result.outcome,
        delivery.outcome,
    )


async def _run_startup_cleanup(application: Application) -> None:
    settings = application.bot_data["settings"]

    if isinstance(settings, AuthenticationSettings):
        await telegram_update_cleanup.run_if_due(settings=settings)


async def _mark_confirmation_sent(*, update_id: int) -> None:
    session_factory = get_async_session_factory()

    try:
        async with session_factory() as session:
            await mark_telegram_processed_update_confirmation_sent(
                session,
                update_id=update_id,
                confirmation_sent_at=datetime.now(timezone.utc),
            )
            await session.commit()
    except SQLAlchemyError:
        logger.error("telegram.confirmation.failed update_id=%s failure_category=recording", update_id)


async def handle_polling_error(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    del update
    failure_category = "webhook_conflict" if isinstance(context.error, Conflict) else "telegram"
    logger.error("telegram.polling.failed failure_category=%s", failure_category)


def main() -> None:
    application = create_application(get_authentication_settings())

    try:
        application.run_polling(
            allowed_updates=[Update.MESSAGE],
            drop_pending_updates=False,
            timeout=30,
        )
    except Conflict:
        logger.error("telegram.polling.failed failure_category=webhook_conflict")
        raise TelegramUpdateProcessorConfigurationError(
            "Telegram polling cannot run while a webhook is configured."
        ) from None
    except TelegramError:
        logger.error("telegram.polling.failed failure_category=telegram")
        raise


if __name__ == "__main__":
    main()
