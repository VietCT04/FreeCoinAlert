import asyncio
import logging
import signal
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import get_authentication_settings
from freecoinalert_api.db.models.notification_outbox import NotificationOutbox
from freecoinalert_api.db.models.signal_event import SignalEvent
from freecoinalert_api.db.models.signal_event_invalidation import SignalEventInvalidation
from freecoinalert_api.db.models.signal_subscription import SignalSubscription
from freecoinalert_api.db.models.telegram_connection import TelegramConnection
from freecoinalert_api.db.repositories.notification_outbox import (
    claim_available_notifications,
    get_notification_by_id_for_update,
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
from freecoinalert_api.notifications.messages import (
    format_preset_signal_message,
    format_price_alert_message,
)
from freecoinalert_api.notifications.payloads import (
    NotificationPayloadError,
    PresetSignalPayload,
    parse_preset_signal_payload,
)
from freecoinalert_api.telegram.client import (
    TelegramBotClient,
    TelegramDeliveryResult,
    TelegramDeliveryOutcome,
)
from freecoinalert_api.telegram.bot import create_telegram_bot

logger = logging.getLogger(__name__)
SUPPORTED_NOTIFICATION_KINDS = (
    "telegram_test",
    "telegram_price_alert",
    "telegram_preset_signal",
)
PRESET_SIGNAL_NOTIFICATION_KIND = "telegram_preset_signal"
STALE_PROCESSING_AFTER = timedelta(minutes=10)
RETRY_DELAYS = {
    1: timedelta(seconds=5),
    2: timedelta(seconds=30),
    3: timedelta(minutes=2),
    4: timedelta(minutes=10),
}


@dataclass(frozen=True, slots=True)
class PresetSignalDeliveryContext:
    chat_id: int
    text: str


class NotificationWorker:
    def __init__(
        self,
        *,
        telegram_client: TelegramBotClient | None,
        worker_id: str,
    ) -> None:
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
                    logger.error(
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
                    kinds=SUPPORTED_NOTIFICATION_KINDS,
                )
                await session.commit()
        except SQLAlchemyError:
            logger.exception("notification.failed failure_category=claim")
            return []

        for notification in notifications:
            logger.info(
                "notification.claimed notification_id=%s kind=%s attempt_count=%s",
                notification.id,
                notification.kind,
                notification.attempt_count,
            )
        return notifications

    async def _deliver(self, notification: NotificationOutbox) -> None:
        if notification.kind == PRESET_SIGNAL_NOTIFICATION_KIND:
            await self._deliver_preset_signal(notification)
            return

        telegram_client = self._telegram_client
        if telegram_client is None:
            await self._fail_before_provider(
                notification,
                failure_code="telegram_not_configured",
            )
            return

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
                    failure_code="telegram_connection_unavailable",
                )
                await session.commit()
                logger.info(
                    "notification.failed notification_id=%s "
                    "failure_category=telegram_connection_unavailable",
                    notification.id,
                )
                return

            chat_id = connection.telegram_chat_id

        if notification.kind == "telegram_test":
            delivery = await telegram_client.send_test_notification(chat_id=chat_id)
        elif notification.kind == "telegram_price_alert":
            delivery = await telegram_client.send_price_alert(
                chat_id=chat_id,
                text=format_price_alert_message(notification.message_payload),
            )
        else:
            async with session_factory() as session:
                await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=datetime.now(timezone.utc),
                    failure_code="notification_kind_invalid",
                )
                await session.commit()
            logger.error(
                "notification.failed notification_id=%s failure_category=kind_invalid",
                notification.id,
            )
            return
        await self._record_delivery(notification, delivery)

    async def _deliver_preset_signal(self, notification: NotificationOutbox) -> None:
        try:
            payload = parse_preset_signal_payload(notification.message_payload)
        except NotificationPayloadError:
            await self._fail_before_provider(
                notification,
                failure_code="notification_payload_invalid",
            )
            return

        telegram_client = self._telegram_client
        if telegram_client is None:
            await self._fail_before_provider(
                notification,
                failure_code="telegram_not_configured",
            )
            return

        delivery_context = await self._prepare_preset_signal_delivery(
            notification,
            payload,
        )
        if delivery_context is None:
            return

        delivery = await telegram_client.send_preset_signal(
            chat_id=delivery_context.chat_id,
            text=delivery_context.text,
        )
        await self._record_delivery(notification, delivery)

    async def _prepare_preset_signal_delivery(
        self,
        notification: NotificationOutbox,
        payload: PresetSignalPayload,
    ) -> PresetSignalDeliveryContext | None:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            current_notification = await get_notification_by_id_for_update(
                session,
                notification_id=notification.id,
            )
            if (
                current_notification is None
                or current_notification.status != "processing"
                or current_notification.locked_by != self._worker_id
            ):
                return None

            failure_code: str | None = None
            if (
                current_notification.kind != PRESET_SIGNAL_NOTIFICATION_KIND
                or current_notification.user_id != notification.user_id
                or current_notification.telegram_connection_id
                != notification.telegram_connection_id
                or current_notification.signal_event_id is None
                or current_notification.signal_subscription_id is None
                or current_notification.signal_event_id != notification.signal_event_id
                or current_notification.signal_subscription_id
                != notification.signal_subscription_id
                or current_notification.signal_event_id != payload.signal_event_id
                or current_notification.signal_subscription_id
                != payload.signal_subscription_id
            ):
                failure_code = "notification_payload_invalid"

            if failure_code is None:
                subscription = await session.get(
                    SignalSubscription,
                    current_notification.signal_subscription_id,
                )
                if (
                    subscription is None
                    or subscription.user_id != current_notification.user_id
                ):
                    failure_code = "signal_subscription_inactive"
                elif subscription.status != "active":
                    failure_code = "signal_subscription_inactive"
                elif not subscription.telegram_delivery_enabled:
                    failure_code = "signal_delivery_preference_disabled"

            if failure_code is None:
                signal_event = await session.get(
                    SignalEvent,
                    current_notification.signal_event_id,
                )
                if signal_event is None:
                    failure_code = "signal_event_invalidated"
                else:
                    invalidation_id = await session.scalar(
                        select(SignalEventInvalidation.id).where(
                            SignalEventInvalidation.signal_event_id == signal_event.id
                        )
                    )
                    if invalidation_id is not None:
                        failure_code = "signal_event_invalidated"

            connection: TelegramConnection | None = None
            if failure_code is None:
                connection = await get_telegram_connection_by_user_id(
                    session,
                    user_id=current_notification.user_id,
                )
                if (
                    connection is None
                    or connection.id != current_notification.telegram_connection_id
                    or connection.status != "connected"
                ):
                    failure_code = "telegram_connection_unavailable"

            if failure_code is not None:
                await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=datetime.now(timezone.utc),
                    failure_code=failure_code,
                )
                await session.commit()
                self._log_pre_provider_failure(notification, failure_code)
                return None

            assert connection is not None
            return PresetSignalDeliveryContext(
                chat_id=connection.telegram_chat_id,
                text=format_preset_signal_message(payload),
            )

    async def _fail_before_provider(
        self,
        notification: NotificationOutbox,
        *,
        failure_code: str,
    ) -> None:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            await mark_notification_failed(
                session,
                notification_id=notification.id,
                failed_at=datetime.now(timezone.utc),
                failure_code=failure_code,
            )
            await session.commit()
        self._log_pre_provider_failure(notification, failure_code)

    @staticmethod
    def _log_pre_provider_failure(
        notification: NotificationOutbox,
        failure_code: str,
    ) -> None:
        logger.info(
            "notification.failed notification_id=%s signal_event_id=%s "
            "failure_category=%s",
            notification.id,
            notification.signal_event_id,
            failure_code,
        )

    async def _record_delivery(
        self,
        notification: NotificationOutbox,
        delivery: TelegramDeliveryResult,
    ) -> None:
        session_factory = get_async_session_factory()
        current_time = datetime.now(timezone.utc)
        async with session_factory() as session:
            updated = False
            if delivery.outcome is TelegramDeliveryOutcome.SENT:
                updated = await mark_notification_sent(
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
                updated = await mark_notification_retry_wait(
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
                updated = await mark_notification_retry_wait(
                    session,
                    notification_id=notification.id,
                    available_at=current_time
                    + RETRY_DELAYS.get(notification.attempt_count, timedelta(minutes=10)),
                    failure_code="telegram_temporary_failure",
                )
                event = "notification.retry_scheduled"
                failure_code = "telegram_temporary_failure"
            elif delivery.outcome is TelegramDeliveryOutcome.PERMANENT_FAILURE:
                updated = await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_destination_unavailable",
                )
                if updated:
                    await mark_telegram_connection_degraded(
                        session,
                        connection_id=notification.telegram_connection_id,
                        degraded_at=current_time,
                        status_reason="telegram_destination_unavailable",
                    )
                event = "telegram.connection.degraded"
                failure_code = "telegram_destination_unavailable"
            elif delivery.outcome is TelegramDeliveryOutcome.NOT_CONFIGURED:
                updated = await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_not_configured",
                )
                event = "notification.failed"
                failure_code = "telegram_not_configured"
            elif delivery.outcome is TelegramDeliveryOutcome.UNCERTAIN:
                updated = await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_delivery_outcome_unknown",
                )
                event = "notification.outcome_unknown"
                failure_code = "telegram_delivery_outcome_unknown"
            else:
                updated = await mark_notification_failed(
                    session,
                    notification_id=notification.id,
                    failed_at=current_time,
                    failure_code="telegram_temporary_failure",
                )
                event = "notification.failed"
                failure_code = "telegram_temporary_failure"

            await session.commit()
        if updated:
            logger.info(
                "%s notification_id=%s signal_event_id=%s failure_category=%s",
                event,
                notification.id,
                notification.signal_event_id,
                failure_code,
            )
        else:
            logger.info(
                "notification.outcome_ignored notification_id=%s signal_event_id=%s",
                notification.id,
                notification.signal_event_id,
            )

    async def _sleep_until_work_or_shutdown(self) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=2)
        except TimeoutError:
            return


def create_worker() -> NotificationWorker:
    settings = get_authentication_settings()
    telegram_client: TelegramBotClient | None = None
    if settings.telegram_bot_token:
        telegram_client = TelegramBotClient(create_telegram_bot(settings))

    return NotificationWorker(
        telegram_client=telegram_client,
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
