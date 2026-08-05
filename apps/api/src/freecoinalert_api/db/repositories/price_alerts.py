import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.price_alert import PriceAlert


async def create_price_alert(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    supported_market_id: uuid.UUID,
    telegram_connection_id: uuid.UUID,
    creation_idempotency_key: str,
    direction: str,
    target_price: Decimal,
    exchange_snapshot: str,
    market_type_snapshot: str,
    symbol_snapshot: str,
    base_asset_snapshot: str,
    quote_asset_snapshot: str,
    price_tick_snapshot: Decimal,
) -> PriceAlert:
    alert = PriceAlert(
        user_id=user_id,
        supported_market_id=supported_market_id,
        telegram_connection_id=telegram_connection_id,
        creation_idempotency_key=creation_idempotency_key,
        kind="price_cross",
        direction=direction,
        target_price=target_price,
        exchange_snapshot=exchange_snapshot,
        market_type_snapshot=market_type_snapshot,
        symbol_snapshot=symbol_snapshot,
        base_asset_snapshot=base_asset_snapshot,
        quote_asset_snapshot=quote_asset_snapshot,
        price_tick_snapshot=price_tick_snapshot,
        status="active",
    )
    session.add(alert)
    await session.flush()
    return alert


async def get_price_alert_for_user(
    session: AsyncSession,
    *,
    alert_id: uuid.UUID,
    user_id: uuid.UUID,
    include_deleted: bool = False,
) -> PriceAlert | None:
    statement = select(PriceAlert).where(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == user_id,
    )

    if not include_deleted:
        statement = statement.where(PriceAlert.status != "deleted")

    return await session.scalar(statement)


async def get_price_alert_for_user_for_update(
    session: AsyncSession,
    *,
    alert_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PriceAlert | None:
    return await session.scalar(
        select(PriceAlert)
        .where(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == user_id,
        )
        .with_for_update()
    )


async def get_price_alert_by_user_and_idempotency_key(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    creation_idempotency_key: str,
) -> PriceAlert | None:
    return await session.scalar(
        select(PriceAlert).where(
            PriceAlert.user_id == user_id,
            PriceAlert.creation_idempotency_key == creation_idempotency_key,
        )
    )


async def list_price_alerts_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    include_deleted: bool = False,
) -> Sequence[PriceAlert]:
    statement = select(PriceAlert).where(PriceAlert.user_id == user_id)

    if not include_deleted:
        statement = statement.where(PriceAlert.status != "deleted")

    statement = statement.order_by(PriceAlert.created_at.desc(), PriceAlert.id.desc())
    return (await session.scalars(statement)).all()


async def list_price_alerts_page_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    status: str | None,
    cursor_created_at: datetime | None,
    cursor_id: uuid.UUID | None,
) -> Sequence[PriceAlert]:
    statement = select(PriceAlert).where(
        PriceAlert.user_id == user_id,
        PriceAlert.status != "deleted",
    )

    if status is not None:
        statement = statement.where(PriceAlert.status == status)

    if cursor_created_at is not None and cursor_id is not None:
        statement = statement.where(
            tuple_(PriceAlert.created_at, PriceAlert.id)
            < tuple_(cursor_created_at, cursor_id)
        )

    statement = statement.order_by(
        PriceAlert.created_at.desc(),
        PriceAlert.id.desc(),
    ).limit(limit)
    return (await session.scalars(statement)).all()


async def lock_user_price_alert_creation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:user_id AS text), 0))"),
        {"user_id": str(user_id)},
    )


async def count_active_price_alerts_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(PriceAlert).where(
                PriceAlert.user_id == user_id,
                PriceAlert.status == "active",
            )
        )
        or 0
    )


async def get_price_alert_by_id_for_update(
    session: AsyncSession,
    *,
    alert_id: uuid.UUID,
) -> PriceAlert | None:
    return await session.scalar(
        select(PriceAlert).where(PriceAlert.id == alert_id).with_for_update()
    )


async def list_active_price_alerts_for_market(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
) -> Sequence[PriceAlert]:
    statement = (
        select(PriceAlert)
        .where(
            PriceAlert.supported_market_id == supported_market_id,
            PriceAlert.status == "active",
        )
        .order_by(PriceAlert.id)
    )
    return (await session.scalars(statement)).all()


async def list_active_price_alerts(session: AsyncSession) -> Sequence[PriceAlert]:
    statement = (
        select(PriceAlert)
        .where(PriceAlert.status == "active")
        .order_by(PriceAlert.supported_market_id, PriceAlert.id)
    )
    return (await session.scalars(statement)).all()


async def list_active_price_alerts_updated_since(
    session: AsyncSession,
    *,
    updated_since: datetime,
) -> Sequence[PriceAlert]:
    statement = (
        select(PriceAlert)
        .where(PriceAlert.updated_at >= updated_since)
        .order_by(PriceAlert.updated_at, PriceAlert.id)
    )
    return (await session.scalars(statement)).all()


async def initialize_price_alert_relation(
    session: AsyncSession,
    *,
    alert: PriceAlert,
    relation: str,
    observed_price: Decimal,
    provider_event_id: int,
    provider_event_time: datetime,
) -> bool:
    if alert.status != "active" or alert.last_relation is not None:
        return False

    alert.last_relation = relation
    alert.last_evaluated_price = observed_price
    alert.last_evaluated_provider_id = provider_event_id
    alert.last_evaluated_provider_time = provider_event_time
    await session.flush()
    return True


async def update_price_alert_relation(
    session: AsyncSession,
    *,
    alert: PriceAlert,
    relation: str,
    observed_price: Decimal,
    provider_event_id: int,
    provider_event_time: datetime,
) -> bool:
    if (
        alert.status != "active"
        or alert.last_relation is None
        or (
            alert.last_evaluated_provider_id is not None
            and provider_event_id <= alert.last_evaluated_provider_id
        )
    ):
        return False

    alert.last_relation = relation
    alert.last_evaluated_price = observed_price
    alert.last_evaluated_provider_id = provider_event_id
    alert.last_evaluated_provider_time = provider_event_time
    await session.flush()
    return True


async def mark_price_alert_triggered(
    session: AsyncSession,
    *,
    alert: PriceAlert,
    triggered_at: datetime,
    relation: str,
    observed_price: Decimal,
    provider_event_id: int,
    provider_event_time: datetime,
) -> bool:
    if (
        alert.status != "active"
        or alert.last_relation is None
        or (
            alert.last_evaluated_provider_id is not None
            and provider_event_id <= alert.last_evaluated_provider_id
        )
    ):
        return False

    alert.status = "triggered"
    alert.triggered_at = triggered_at
    alert.last_relation = relation
    alert.last_evaluated_price = observed_price
    alert.last_evaluated_provider_id = provider_event_id
    alert.last_evaluated_provider_time = provider_event_time
    await session.flush()
    return True


async def mark_price_alert_disabled(
    session: AsyncSession,
    *,
    alert: PriceAlert,
    disabled_at: datetime,
    reason: str,
) -> bool:
    if alert.status != "active":
        return False

    alert.status = "disabled"
    alert.status_reason = reason
    alert.disabled_at = disabled_at
    await session.flush()
    return True


async def mark_price_alert_deleted(
    session: AsyncSession,
    *,
    alert: PriceAlert,
    deleted_at: datetime,
) -> bool:
    if alert.status not in {"active", "disabled"}:
        return False

    alert.status = "deleted"
    alert.status_reason = "user_deleted"
    alert.disabled_at = None
    alert.deleted_at = deleted_at
    await session.flush()
    return True


async def mark_price_alert_failed(
    session: AsyncSession,
    *,
    alert: PriceAlert,
    failed_at: datetime,
    reason: str,
) -> bool:
    if alert.status != "active":
        return False

    alert.status = "failed"
    alert.status_reason = reason
    alert.failed_at = failed_at
    await session.flush()
    return True
