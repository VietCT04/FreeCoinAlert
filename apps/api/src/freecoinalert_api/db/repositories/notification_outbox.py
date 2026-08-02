import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.notification_outbox import NotificationOutbox


async def get_notification_by_user_and_idempotency_key(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> NotificationOutbox | None:
    return await session.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.user_id == user_id,
            NotificationOutbox.idempotency_key == idempotency_key,
        )
    )


async def get_notification_by_id_and_user_id(
    session: AsyncSession,
    *,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> NotificationOutbox | None:
    return await session.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.id == notification_id,
            NotificationOutbox.user_id == user_id,
        )
    )


async def create_telegram_test_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    telegram_connection_id: uuid.UUID,
    idempotency_key: str,
) -> NotificationOutbox:
    notification = NotificationOutbox(
        user_id=user_id,
        telegram_connection_id=telegram_connection_id,
        kind="telegram_test",
        status="pending",
        idempotency_key=idempotency_key,
        message_payload={"schemaVersion": 1, "messageType": "telegram_test"},
    )
    session.add(notification)
    await session.flush()
    return notification


async def create_telegram_price_alert_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    telegram_connection_id: uuid.UUID,
    alert_id: uuid.UUID,
    alert_event_id: uuid.UUID,
    symbol: str,
    base_asset: str,
    quote_asset: str,
    direction: str,
    target_price: Decimal,
    trigger_price: Decimal,
    triggered_at: datetime,
) -> NotificationOutbox:
    notification = NotificationOutbox(
        user_id=user_id,
        telegram_connection_id=telegram_connection_id,
        kind="telegram_price_alert",
        status="pending",
        idempotency_key=f"price-alert:{alert_id}",
        message_payload={
            "schemaVersion": 1,
            "messageType": "telegram_price_alert",
            "alertEventId": str(alert_event_id),
            "symbol": symbol,
            "baseAsset": base_asset,
            "quoteAsset": quote_asset,
            "direction": direction,
            "targetPrice": format(target_price, "f"),
            "triggerPrice": format(trigger_price, "f"),
            "triggeredAt": triggered_at.isoformat(),
        },
    )
    session.add(notification)
    await session.flush()
    return notification


async def create_telegram_preset_signal_notification(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    telegram_connection_id: uuid.UUID,
    signal_event_id: uuid.UUID,
    signal_subscription_id: uuid.UUID,
    message_payload: dict[str, Any],
) -> NotificationOutbox | None:
    result = await session.execute(
        insert(NotificationOutbox)
        .values(
            user_id=user_id,
            telegram_connection_id=telegram_connection_id,
            signal_event_id=signal_event_id,
            signal_subscription_id=signal_subscription_id,
            kind="telegram_preset_signal",
            status="pending",
            idempotency_key=f"preset-signal:{signal_event_id}",
            message_payload=message_payload,
        )
        .on_conflict_do_nothing()
        .returning(NotificationOutbox.id)
    )
    notification_id = result.scalar_one_or_none()
    if notification_id is None:
        return None
    notification = await session.get(NotificationOutbox, notification_id)
    if notification is None:
        raise RuntimeError("The inserted preset-signal notification was not found.")
    return notification


async def claim_available_notifications(
    session: AsyncSession,
    *,
    current_time: datetime,
    worker_id: str,
    kinds: Sequence[str],
    limit: int = 10,
) -> list[NotificationOutbox]:
    notifications = list(
        (
            await session.scalars(
                select(NotificationOutbox)
                .where(
                    NotificationOutbox.status.in_(("pending", "retry_wait")),
                    NotificationOutbox.kind.in_(kinds),
                    NotificationOutbox.available_at <= current_time,
                )
                .order_by(NotificationOutbox.available_at, NotificationOutbox.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    for notification in notifications:
        notification.status = "processing"
        notification.locked_at = current_time
        notification.locked_by = worker_id
        notification.attempt_count += 1
    await session.flush()
    return notifications


async def recover_stale_processing_notifications(
    session: AsyncSession,
    *,
    stale_before: datetime,
    failed_at: datetime,
) -> int:
    result = await session.execute(
        update(NotificationOutbox)
        .where(
            NotificationOutbox.status == "processing",
            NotificationOutbox.locked_at < stale_before,
        )
        .values(
            status="failed",
            locked_at=None,
            locked_by=None,
            failed_at=failed_at,
            failure_code="telegram_delivery_outcome_unknown",
            updated_at=func.now(),
        )
    )
    return result.rowcount



async def mark_notification_sent(
    session: AsyncSession,
    *,
    notification_id: uuid.UUID,
    sent_at: datetime,
    provider_message_id: int,
) -> None:
    await session.execute(
        update(NotificationOutbox)
        .where(NotificationOutbox.id == notification_id)
        .values(
            status="sent",
            locked_at=None,
            locked_by=None,
            sent_at=sent_at,
            failed_at=None,
            failure_code=None,
            provider_message_id=provider_message_id,
            updated_at=func.now(),
        )
    )


async def mark_notification_retry_wait(
    session: AsyncSession,
    *,
    notification_id: uuid.UUID,
    available_at: datetime,
    failure_code: str,
) -> None:
    await session.execute(
        update(NotificationOutbox)
        .where(NotificationOutbox.id == notification_id)
        .values(
            status="retry_wait",
            available_at=available_at,
            locked_at=None,
            locked_by=None,
            failed_at=None,
            failure_code=failure_code,
            updated_at=func.now(),
        )
    )


async def mark_notification_failed(
    session: AsyncSession,
    *,
    notification_id: uuid.UUID,
    failed_at: datetime,
    failure_code: str,
) -> None:
    await session.execute(
        update(NotificationOutbox)
        .where(NotificationOutbox.id == notification_id)
        .values(
            status="failed",
            locked_at=None,
            locked_by=None,
            failed_at=failed_at,
            failure_code=failure_code,
            updated_at=func.now(),
        )
    )
