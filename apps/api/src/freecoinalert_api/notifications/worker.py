import asyncio
import logging
import signal
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import get_authentication_settings
from freecoinalert_api.db.models.notification_outbox import NotificationOutbox
from freecoinalert_api.db.repositories.notification_outbox import (
    claim_available_notifications,
    mark_notification_failed,
    mark_notification_retry_wait,
    mark_notification_sent,
    recover_stale_processing_notifications,
)
from freecoinalert_api.db.repositories.telegram import (
    get_telegram_connection_by_user_id,
    mark_telegram_connection_degraded,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.telegram.client import (
    TelegramBotClient,
    TelegramDeliveryResult,
    TelegramDeliveryOutcome,
)
from freecoinalert_api.telegram.poller import TelegramUpdateProcessorConfigurationError

logger = logging.getLogger(__name__)
STALE_PROCESSING_AFTER = timedelta(minutes=10)
RETRY_DELAYS = {
    1: timedelta(seconds=5),
    2: timedelta(seconds=30),
    3: timedelta(minutes=2),
    4: timedelta(minutes=10),
}


class NotificationWorker:
    def __init__(self, *, telegram_client: TelegramBotClient, worker_id: str) -> None:
        self._telegram_client = telegram_client
        self._worker_id = worker_id
        self._stop_event = asyncio.Event()
        self._next_stale_recovery_at = datetime.now(timezone.utc)

    def request_shutdown(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        await self._recover_stale_notifications()
        while not self._stop_event.is_set():
            if datetime.now(timezone.utc) >= self._next_stale_recovery_at:
                await self._recover_stale_notifications()
            claimed_notifications = await self._claim_notifications()
            if not claimed_notifications:
                await self._sleep_until_work_or_shutdown()
                continue

            for notification in claimed_notifications:
                if self._stop_event.is_set():
                    break
                try:
                    await self._deliver(notification)
                except Exception:
                    logger.exception(
                        "notification.failed notification_id=%s failure_category=worker_error",
                        notification.id,
                    )

    async def _recover_stale_notifications(self) -> None:
        current_time = datetime.now(timezone.utc)
        self._next_stale_recovery_at = current_time + timedelta(minutes=10)
        session_factory = get_async_session_factory()
        try:
            async with session_factory() as session:
                recovered_count = await recover_stale_processing_notifications(
                    session,
                    stale_before=current_time - STALE_PROCESSING_AFTER,
                    failed_at=current_time,
                )
                await session.commit()
            if recovered_count:
                logger.warning(
                    "notification.outcome_unknown recovered_count=%s",
                    recovered_count,
                )
        except SQLAlchemyError:
            logger.exception("notification.failed failure_category=stale_recovery")

    async def _claim_notifications(self) -> list[NotificationOutbox]:
        session_factory = get_async_session_factory()
        current_time = datetime.now(timezone.utc)
        try:
            async with session_factory() as session:
                notifications = await claim_available_notifications(
                    session,
                    current_time=current_time,
                    worker_id=self._worker_id,
                )
                await session.commit()
        except SQLAlchemyError:
            logger.exception("notification.failed failure_category=claim")
            return []

        for notification in notifications:
            logger.info(
                "notification.claimed notification_id=%s user_id=%s attempt_count=%s",
                notification.id,
                notification.user_id,
                notification.attempt_count,
            )
        return notifications

    async def _deliver(self, notification: NotificationOutbox) -> None:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            connection = await get_telegram_connection_by_user_id(
                session,
                user_id=notification.user_id,
            )

            if (
                connection is None
                or connection.id != notification.telegram_connection_id
                or connection.status != "connected"
            ):
                await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=datetime.now(timezone.utc),
                    failure_code="telegram_not_connected",
                )
                await session.commit()
                logger.info(
                    "notification.failed notification_id=%s failure_category=telegram_not_connected",
                    notification.id,
                )
                return

            chat_id = connection.telegram_chat_id

        delivery = await self._telegram_client.send_test_notification(chat_id=chat_id)
        await self._record_delivery(notification, delivery)

    async def _record_delivery(
        self,
        notification: NotificationOutbox,
        delivery: TelegramDeliveryResult,
    ) -> None:
        session_factory = get_async_session_factory()
        current_time = datetime.now(timezone.utc)
        async with session_factory() as session:
            if delivery.outcome is TelegramDeliveryOutcome.SENT:
                await mark_notification_sent(
                    session,
                    notification_id=notification.id,
                    sent_at=current_time,
                    provider_message_id=delivery.provider_message_id or 0,
                )
                event = "notification.sent"
                failure_code = None
            elif (
                delivery.outcome is TelegramDeliveryOutcome.RATE_LIMITED
                and notification.attempt_count < notification.max_attempts
            ):
                await mark_notification_retry_wait(
                    session,
                    notification_id=notification.id,
                    available_at=current_time
                    + timedelta(seconds=delivery.retry_after_seconds or 1),
                    failure_code="telegram_rate_limited",
                )
                event = "notification.retry_scheduled"
                failure_code = "telegram_rate_limited"
            elif delivery.outcome is TelegramDeliveryOutcome.TEMPORARY_FAILURE and (
                notification.attempt_count < notification.max_attempts
            ):
                await mark_notification_retry_wait(
                    session,
                    notification_id=notification.id,
                    available_at=current_time
                    + RETRY_DELAYS.get(notification.attempt_count, timedelta(minutes=10)),
                    failure_code="telegram_temporary_failure",
                )
                event = "notification.retry_scheduled"
                failure_code = "telegram_temporary_failure"
            elif delivery.outcome is TelegramDeliveryOutcome.PERMANENT_FAILURE:
                await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_destination_unavailable",
                )
                await mark_telegram_connection_degraded(
                    session,
                    connection_id=notification.telegram_connection_id,
                    degraded_at=current_time,
                    status_reason="telegram_destination_unavailable",
                )
                event = "telegram.connection.degraded"
                failure_code = "telegram_destination_unavailable"
            elif delivery.outcome is TelegramDeliveryOutcome.NOT_CONFIGURED:
                await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_not_configured",
                )
                event = "notification.failed"
                failure_code = "telegram_not_configured"
            elif delivery.outcome is TelegramDeliveryOutcome.UNCERTAIN:
                await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_delivery_outcome_unknown",
                )
                event = "notification.outcome_unknown"
                failure_code = "telegram_delivery_outcome_unknown"
            else:
                await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_temporary_failure",
                )
                event = "notification.failed"
                failure_code = "telegram_temporary_failure"

            await session.commit()
        logger.info(
            "%s notification_id=%s failure_category=%s",
            event,
            notification.id,
            failure_code,
        )

    async def _sleep_until_work_or_shutdown(self) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=2)
        except TimeoutError:
            return


def create_worker() -> NotificationWorker:
    settings = get_authentication_settings()
    if not settings.telegram_bot_token:
        raise TelegramUpdateProcessorConfigurationError(
            "Telegram notification processing is not configured."
        )

    from telegram import Bot

    return NotificationWorker(
        telegram_client=TelegramBotClient(Bot(settings.telegram_bot_token)),
        worker_id=str(uuid.uuid4()),
    )


def main() -> None:
    worker = create_worker()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, worker.request_shutdown)
        except NotImplementedError:
            signal.signal(signal_name, lambda *_: worker.request_shutdown())
    try:
        loop.run_until_complete(worker.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
