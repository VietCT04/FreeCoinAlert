import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.notification_outbox import NotificationOutbox
from freecoinalert_api.db.repositories.notification_outbox import (
    create_telegram_test_notification,
    get_notification_by_id_and_user_id,
    get_notification_by_user_and_idempotency_key,
)
from freecoinalert_api.db.repositories.telegram import get_telegram_connection_by_user_id
from freecoinalert_api.notifications.errors import NotificationError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class QueuedNotification:
    notification: NotificationOutbox
    created: bool


class NotificationService:
    async def get_existing_idempotent_notification(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        idempotency_key: str,
    ) -> NotificationOutbox | None:
        return await get_notification_by_user_and_idempotency_key(
            session,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )

    async def queue_test_notification(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        idempotency_key: str,
    ) -> QueuedNotification:
        existing = await self.get_existing_idempotent_notification(
            session,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return QueuedNotification(notification=existing, created=False)

        connection = await get_telegram_connection_by_user_id(
            session,
            user_id=user_id,
            for_update=True,
        )
        if connection is None or connection.status == "disconnected":
            raise NotificationError(
                status_code=409,
                code="TELEGRAM_NOT_CONNECTED",
                message="Connect Telegram before requesting a test notification.",
            )
        if connection.status == "degraded":
            raise NotificationError(
                status_code=409,
                code="TELEGRAM_CONNECTION_DEGRADED",
                message="Reconnect Telegram before requesting a test notification.",
            )

        try:
            notification = await create_telegram_test_notification(
                session,
                user_id=user_id,
                telegram_connection_id=connection.id,
                idempotency_key=idempotency_key,
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            notification = await self.get_existing_idempotent_notification(
                session,
                user_id=user_id,
                idempotency_key=idempotency_key,
            )
            if notification is not None:
                return QueuedNotification(notification=notification, created=False)
            raise NotificationError(
                status_code=503,
                code="TELEGRAM_NOTIFICATION_UNAVAILABLE",
                message="The test notification could not be queued. Try again later.",
            ) from None
        except SQLAlchemyError:
            await session.rollback()
            raise NotificationError(
                status_code=503,
                code="TELEGRAM_NOTIFICATION_UNAVAILABLE",
                message="The test notification could not be queued. Try again later.",
            ) from None

        logger.info("notification.queued notification_id=%s user_id=%s", notification.id, user_id)
        return QueuedNotification(notification=notification, created=True)

    async def get_notification(
        self,
        session: AsyncSession,
        *,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> NotificationOutbox:
        notification = await get_notification_by_id_and_user_id(
            session,
            notification_id=notification_id,
            user_id=user_id,
        )
        if notification is None:
            raise NotificationError(
                status_code=404,
                code="TELEGRAM_NOTIFICATION_NOT_FOUND",
                message="The test notification was not found.",
            )
        return notification


notification_service = NotificationService()
