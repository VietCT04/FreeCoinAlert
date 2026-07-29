import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.telegram_link_token import TelegramLinkToken
from freecoinalert_api.db.models.telegram_processed_update import TelegramProcessedUpdate
from freecoinalert_api.db.repositories.telegram import (
    consume_telegram_link_token,
    create_telegram_connection,
    get_telegram_link_token_by_hash,
    get_telegram_connection_by_identifiers,
    get_telegram_connection_by_user_id,
    reactivate_telegram_connection,
    record_processed_telegram_update,
)

logger = logging.getLogger(__name__)

TelegramLinkOutcome = Literal[
    "linked",
    "already_linked",
    "invalid_token",
    "expired_token",
    "consumed_token",
    "revoked_token",
    "ownership_conflict",
]


@dataclass(frozen=True, slots=True)
class TelegramLinkResult:
    outcome: TelegramLinkOutcome
    connection_id: UUID | None
    should_confirm: bool


class TelegramUpdateLinkingService:
    async def process_link(
        self,
        session: AsyncSession,
        *,
        update_id: int,
        raw_token: str,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: str | None,
    ) -> TelegramLinkResult | None:
        now = datetime.now(timezone.utc)
        token_hash = hashlib.sha256(raw_token.encode("ascii")).digest()

        try:
            await record_processed_telegram_update(
                session,
                update_id=update_id,
                outcome="unsupported_update",
                connection_id=None,
                received_at=now,
                processed_at=now,
            )
        except IntegrityError:
            await session.rollback()
            logger.info("telegram.update.duplicate update_id=%s", update_id)
            return None

        try:
            token = await get_telegram_link_token_by_hash(
                session,
                token_hash=token_hash,
                for_update=True,
            )
            outcome = _token_outcome(token, now)

            if outcome is not None:
                return await self._finish(
                    session,
                    update_id=update_id,
                    outcome=outcome,
                    connection_id=None,
                    should_confirm=False,
                )

            if token is None:
                raise RuntimeError("A valid token must be present.")

            user_connection = await get_telegram_connection_by_user_id(
                session,
                user_id=token.user_id,
                for_update=True,
            )
            destination_connection = await get_telegram_connection_by_identifiers(
                session,
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                for_update=True,
            )

            if destination_connection is not None and destination_connection.user_id != token.user_id:
                await consume_telegram_link_token(session, token_id=token.id, consumed_at=now)
                return await self._finish(
                    session,
                    update_id=update_id,
                    outcome="ownership_conflict",
                    connection_id=None,
                    should_confirm=False,
                )

            if user_connection is None:
                connection = await create_telegram_connection(
                    session,
                    user_id=token.user_id,
                    telegram_user_id=telegram_user_id,
                    telegram_chat_id=telegram_chat_id,
                    telegram_username=telegram_username,
                    connected_at=now,
                    last_verified_at=now,
                )
                outcome = "linked"
            elif (
                user_connection.telegram_user_id == telegram_user_id
                and user_connection.telegram_chat_id == telegram_chat_id
                and user_connection.status == "disconnected"
            ):
                connection = await reactivate_telegram_connection(
                    session,
                    connection_id=user_connection.id,
                    connected_at=now,
                    last_verified_at=now,
                    telegram_username=telegram_username,
                )

                if connection is None:
                    raise RuntimeError("The locked Telegram connection is missing.")

                outcome = "linked"
            elif (
                user_connection.telegram_user_id == telegram_user_id
                and user_connection.telegram_chat_id == telegram_chat_id
                and user_connection.status == "connected"
            ):
                user_connection.last_verified_at = now
                user_connection.telegram_username = telegram_username
                await session.flush()
                connection = user_connection
                outcome = "already_linked"
            else:
                await consume_telegram_link_token(session, token_id=token.id, consumed_at=now)
                return await self._finish(
                    session,
                    update_id=update_id,
                    outcome="ownership_conflict",
                    connection_id=None,
                    should_confirm=False,
                )

            await consume_telegram_link_token(session, token_id=token.id, consumed_at=now)
            return await self._finish(
                session,
                update_id=update_id,
                outcome=outcome,
                connection_id=connection.id,
                should_confirm=True,
            )
        except (IntegrityError, SQLAlchemyError):
            await session.rollback()
            logger.error("telegram.link.rejected failure_category=database")
            return None

    @staticmethod
    async def _finish(
        session: AsyncSession,
        *,
        update_id: int,
        outcome: TelegramLinkOutcome,
        connection_id: UUID | None,
        should_confirm: bool,
    ) -> TelegramLinkResult:
        processed_update = await session.get(TelegramProcessedUpdate, update_id)

        if processed_update is None:
            raise RuntimeError("The processed Telegram update is missing.")

        processed_update.outcome = outcome
        processed_update.connection_id = connection_id
        await session.commit()
        logger.info(
            "telegram.link.%s update_id=%s connection_id=%s",
            "succeeded" if should_confirm else "rejected",
            update_id,
            connection_id,
        )
        return TelegramLinkResult(
            outcome=outcome,
            connection_id=connection_id,
            should_confirm=should_confirm,
        )


def _token_outcome(
    token: TelegramLinkToken | None,
    now: datetime,
) -> TelegramLinkOutcome | None:
    if token is None:
        return "invalid_token"

    if token.expires_at <= now:
        return "expired_token"

    if token.consumed_at is not None:
        return "consumed_token"

    if token.revoked_at is not None:
        return "revoked_token"

    return None


telegram_update_linking_service = TelegramUpdateLinkingService()
