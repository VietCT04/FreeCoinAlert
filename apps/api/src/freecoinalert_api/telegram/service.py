from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.core.config import Settings
from freecoinalert_api.db.models.telegram_connection import TelegramConnection
from freecoinalert_api.db.repositories.telegram import (
    create_telegram_link_token,
    get_active_telegram_link_token_by_user_id,
    get_telegram_connection_by_user_id,
    mark_telegram_connection_disconnected,
    revoke_outstanding_telegram_link_tokens,
)
from freecoinalert_api.telegram.errors import TelegramError
from freecoinalert_api.telegram.links import create_link_token

TelegramConnectionStatus = Literal[
    "not_connected",
    "linking",
    "connected",
    "degraded",
    "disconnected",
]


@dataclass(frozen=True, slots=True)
class SafeTelegramConnection:
    status: TelegramConnectionStatus
    username: str | None = None
    connected_at: datetime | None = None
    last_verified_at: datetime | None = None
    link_expires_at: datetime | None = None
    status_reason: str | None = None


@dataclass(frozen=True, slots=True)
class TelegramLink:
    connection: SafeTelegramConnection
    url: str


class TelegramConnectionService:
    async def create_link(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        settings: Settings,
    ) -> TelegramLink:
        self.require_configuration(settings)

        now = datetime.now(timezone.utc)
        try:
            connection = await get_telegram_connection_by_user_id(
                session,
                user_id=user_id,
                for_update=True,
            )
        except SQLAlchemyError as error:
            await session.rollback()
            del error
            raise TelegramError(
                status_code=503,
                code="TELEGRAM_LINK_UNAVAILABLE",
                message="Telegram linking is temporarily unavailable.",
            ) from None

        if connection is not None and connection.status in {"connected", "degraded"}:
            raise TelegramError(
                status_code=409,
                code="TELEGRAM_ALREADY_CONNECTED",
                message=(
                    "Telegram is already connected. Disconnect it before connecting another account."
                ),
            )

        raw_token, token_hash = create_link_token()
        expires_at = now + timedelta(seconds=settings.telegram_link_ttl_seconds)

        try:
            await revoke_outstanding_telegram_link_tokens(
                session,
                user_id=user_id,
                revoked_at=now,
            )
            await create_telegram_link_token(
                session,
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            del error
            raise TelegramError(
                status_code=503,
                code="TELEGRAM_LINK_UNAVAILABLE",
                message="Telegram linking is temporarily unavailable.",
            ) from None
        except SQLAlchemyError as error:
            await session.rollback()
            del error
            raise TelegramError(
                status_code=503,
                code="TELEGRAM_LINK_UNAVAILABLE",
                message="Telegram linking is temporarily unavailable.",
            ) from None

        return TelegramLink(
            connection=SafeTelegramConnection(
                status="linking",
                link_expires_at=expires_at,
            ),
            url=f"https://t.me/{settings.telegram_bot_username}?start={raw_token}",
        )

    async def get_connection(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
    ) -> SafeTelegramConnection:
        now = datetime.now(timezone.utc)
        try:
            connection = await get_telegram_connection_by_user_id(session, user_id=user_id)
            active_link_token = await get_active_telegram_link_token_by_user_id(
                session,
                user_id=user_id,
                current_time=now,
            )
        except SQLAlchemyError as error:
            await session.rollback()
            del error
            raise TelegramError(
                status_code=503,
                code="TELEGRAM_CONNECTION_UNAVAILABLE",
                message="Telegram connection management is temporarily unavailable.",
            ) from None

        if connection is None:
            if active_link_token is None:
                return SafeTelegramConnection(status="not_connected")

            return SafeTelegramConnection(
                status="linking",
                link_expires_at=active_link_token.expires_at,
            )

        if connection.status == "disconnected" and active_link_token is not None:
            return SafeTelegramConnection(
                status="linking",
                link_expires_at=active_link_token.expires_at,
            )

        return self._safe_connection(connection)

    async def disconnect(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
    ) -> None:
        now = datetime.now(timezone.utc)

        try:
            connection = await get_telegram_connection_by_user_id(
                session,
                user_id=user_id,
                for_update=True,
            )

            if connection is not None and connection.status != "disconnected":
                await mark_telegram_connection_disconnected(
                    session,
                    connection_id=connection.id,
                    disconnected_at=now,
                    status_reason="user_disconnected",
                )

            await revoke_outstanding_telegram_link_tokens(
                session,
                user_id=user_id,
                revoked_at=now,
            )
            await session.commit()
        except SQLAlchemyError as error:
            await session.rollback()
            del error
            raise TelegramError(
                status_code=503,
                code="TELEGRAM_CONNECTION_UNAVAILABLE",
                message="Telegram connection management is temporarily unavailable.",
            ) from None

    @staticmethod
    def require_configuration(settings: Settings) -> None:
        if settings.telegram_bot_username is None:
            raise TelegramError(
                status_code=503,
                code="TELEGRAM_NOT_CONFIGURED",
                message="Telegram linking is not configured.",
            )

    @staticmethod
    def _safe_connection(connection: TelegramConnection) -> SafeTelegramConnection:
        return SafeTelegramConnection(
            status=connection.status,
            username=connection.telegram_username,
            connected_at=connection.connected_at,
            last_verified_at=connection.last_verified_at,
            status_reason=_safe_status_reason(connection.status_reason),
        )


def _safe_status_reason(status_reason: str | None) -> str | None:
    if status_reason is None:
        return None

    if status_reason.replace("_", "").isalnum() and status_reason == status_reason.lower():
        return status_reason

    return None


telegram_connection_service = TelegramConnectionService()
