import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_subscription import SignalSubscription
from freecoinalert_api.db.models.signal_subscription_state_event import SignalSubscriptionStateEvent


async def lock_user_subscription_creation(session: AsyncSession, *, user_id: uuid.UUID) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:user_id AS text), 0))"),
        {"user_id": str(user_id)},
    )


async def count_active_subscriptions_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> int:
    return int(await session.scalar(select(func.count()).select_from(SignalSubscription).where(SignalSubscription.user_id == user_id, SignalSubscription.status == "active")) or 0)


async def get_subscription_for_user(session: AsyncSession, *, user_id: uuid.UUID, subscription_id: uuid.UUID, for_update: bool = False) -> SignalSubscription | None:
    statement = select(SignalSubscription).where(SignalSubscription.user_id == user_id, SignalSubscription.id == subscription_id)
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_subscription_combination_for_update(session: AsyncSession, *, user_id: uuid.UUID, supported_market_id: uuid.UUID, signal_preset_id: uuid.UUID) -> SignalSubscription | None:
    return await session.scalar(select(SignalSubscription).where(SignalSubscription.user_id == user_id, SignalSubscription.supported_market_id == supported_market_id, SignalSubscription.signal_preset_id == signal_preset_id).with_for_update())


async def list_subscriptions_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> Sequence[SignalSubscription]:
    return (await session.scalars(select(SignalSubscription).where(SignalSubscription.user_id == user_id).order_by(SignalSubscription.created_at.desc(), SignalSubscription.id.desc()))).all()


async def list_active_subscriptions_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> Sequence[SignalSubscription]:
    return (await session.scalars(select(SignalSubscription).where(SignalSubscription.user_id == user_id, SignalSubscription.status == "active").order_by(SignalSubscription.id))).all()


async def list_active_subscriber_user_ids(session: AsyncSession, *, supported_market_id: uuid.UUID, signal_preset_id: uuid.UUID) -> Sequence[uuid.UUID]:
    return (await session.scalars(select(SignalSubscription.user_id).where(SignalSubscription.supported_market_id == supported_market_id, SignalSubscription.signal_preset_id == signal_preset_id, SignalSubscription.status == "active").order_by(SignalSubscription.user_id))).all()


async def create_subscription(session: AsyncSession, *, user_id: uuid.UUID, supported_market_id: uuid.UUID, signal_preset_id: uuid.UUID, activated_at: datetime) -> SignalSubscription:
    subscription = SignalSubscription(
        user_id=user_id,
        supported_market_id=supported_market_id,
        signal_preset_id=signal_preset_id,
        status="active",
        activated_at=activated_at,
        telegram_delivery_enabled=False,
        telegram_delivery_changed_at=None,
    )
    session.add(subscription)
    await session.flush()
    await record_subscription_state_event(
        session,
        subscription=subscription,
        effective_at=activated_at,
    )
    return subscription


async def disable_subscription(session: AsyncSession, *, subscription: SignalSubscription, disabled_at: datetime, reason: str) -> None:
    subscription.status = "disabled"
    subscription.status_reason = reason
    subscription.disabled_at = disabled_at
    subscription.telegram_delivery_enabled = False
    subscription.telegram_delivery_changed_at = None
    await session.flush()
    await record_subscription_state_event(
        session,
        subscription=subscription,
        effective_at=disabled_at,
    )


async def reactivate_subscription(
    session: AsyncSession,
    *,
    subscription: SignalSubscription,
    activated_at: datetime,
) -> None:
    subscription.status = "active"
    subscription.status_reason = None
    subscription.activated_at = activated_at
    subscription.disabled_at = None
    subscription.telegram_delivery_enabled = False
    subscription.telegram_delivery_changed_at = None
    await session.flush()
    await record_subscription_state_event(
        session,
        subscription=subscription,
        effective_at=activated_at,
    )


async def update_telegram_delivery_preference(
    session: AsyncSession,
    *,
    subscription: SignalSubscription,
    enabled: bool,
    changed_at: datetime,
) -> None:
    subscription.telegram_delivery_enabled = enabled
    subscription.telegram_delivery_changed_at = changed_at
    await session.flush()
    await record_subscription_state_event(
        session,
        subscription=subscription,
        effective_at=changed_at,
    )


async def record_subscription_state_event(
    session: AsyncSession,
    *,
    subscription: SignalSubscription,
    effective_at: datetime,
) -> SignalSubscriptionStateEvent:
    state_event = SignalSubscriptionStateEvent(
        subscription_id=subscription.id,
        user_id=subscription.user_id,
        supported_market_id=subscription.supported_market_id,
        signal_preset_id=subscription.signal_preset_id,
        subscription_status=subscription.status,
        telegram_delivery_enabled=subscription.telegram_delivery_enabled,
        effective_at=effective_at,
    )
    session.add(state_event)
    await session.flush()
    return state_event


async def disable_subscriptions_for_preset(session: AsyncSession, *, signal_preset_id: uuid.UUID, disabled_at: datetime) -> int:
    subscriptions = (await session.scalars(select(SignalSubscription).where(SignalSubscription.signal_preset_id == signal_preset_id, SignalSubscription.status == "active").with_for_update())).all()
    for subscription in subscriptions:
        await disable_subscription(session, subscription=subscription, disabled_at=disabled_at, reason="preset_disabled")
    return len(subscriptions)
