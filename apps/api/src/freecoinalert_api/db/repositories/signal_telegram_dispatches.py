import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_event import SignalEvent
from freecoinalert_api.db.models.signal_subscription_state_event import (
    SignalSubscriptionStateEvent,
)
from freecoinalert_api.db.models.signal_telegram_dispatch import SignalTelegramDispatch
from freecoinalert_api.db.models.telegram_connection import TelegramConnection


@dataclass(frozen=True, slots=True)
class EligibleSignalSubscription:
    subscription_id: uuid.UUID
    user_id: uuid.UUID
    telegram_connection_id: uuid.UUID | None
    telegram_connection_status: str | None
    telegram_connected_at: datetime | None


async def create_signal_telegram_dispatch(
    session: AsyncSession,
    *,
    signal_event: SignalEvent,
) -> SignalTelegramDispatch:
    backfilled = signal_event.backfilled
    dispatch = SignalTelegramDispatch(
        signal_event_id=signal_event.id,
        status="skipped" if backfilled else "pending",
        completed_at=signal_event.created_at if backfilled else None,
        failure_code="historical_backfill_not_delivered" if backfilled else None,
    )
    session.add(dispatch)
    await session.flush()
    return dispatch


async def recover_stale_signal_telegram_dispatches(
    session: AsyncSession,
    *,
    stale_before: datetime,
    available_at: datetime,
) -> int:
    result = await session.execute(
        update(SignalTelegramDispatch)
        .where(
            SignalTelegramDispatch.status == "processing",
            SignalTelegramDispatch.locked_at < stale_before,
        )
        .values(
            status="pending",
            available_at=available_at,
            locked_at=None,
            locked_by=None,
            failure_code="signal_telegram_dispatch_claim_stale",
            updated_at=func.now(),
        )
    )
    return result.rowcount or 0


async def fail_exhausted_signal_telegram_dispatches(
    session: AsyncSession,
    *,
    failed_at: datetime,
) -> int:
    result = await session.execute(
        update(SignalTelegramDispatch)
        .where(
            SignalTelegramDispatch.status.in_(("pending", "retry_wait")),
            SignalTelegramDispatch.attempt_count >= SignalTelegramDispatch.max_attempts,
        )
        .values(
            status="failed",
            locked_at=None,
            locked_by=None,
            failed_at=failed_at,
            failure_code="signal_telegram_fanout_attempts_exhausted",
            updated_at=func.now(),
        )
    )
    return result.rowcount or 0


async def claim_signal_telegram_dispatches(
    session: AsyncSession,
    *,
    current_time: datetime,
    dispatcher_id: str,
    limit: int,
) -> list[SignalTelegramDispatch]:
    dispatches = list(
        (
            await session.scalars(
                select(SignalTelegramDispatch)
                .where(
                    SignalTelegramDispatch.status.in_(("pending", "retry_wait")),
                    SignalTelegramDispatch.available_at <= current_time,
                    SignalTelegramDispatch.attempt_count
                    < SignalTelegramDispatch.max_attempts,
                )
                .order_by(
                    SignalTelegramDispatch.available_at,
                    SignalTelegramDispatch.created_at,
                    SignalTelegramDispatch.id,
                )
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    for dispatch in dispatches:
        dispatch.status = "processing"
        dispatch.locked_at = current_time
        dispatch.locked_by = dispatcher_id
        dispatch.attempt_count += 1
    await session.flush()
    return dispatches


async def get_signal_telegram_dispatch_for_update(
    session: AsyncSession,
    *,
    dispatch_id: uuid.UUID,
) -> SignalTelegramDispatch | None:
    return await session.scalar(
        select(SignalTelegramDispatch)
        .where(SignalTelegramDispatch.id == dispatch_id)
        .with_for_update()
    )


async def list_eligible_signal_subscriptions(
    session: AsyncSession,
    *,
    signal_event: SignalEvent,
    after_subscription_id: uuid.UUID | None,
    limit: int,
) -> Sequence[EligibleSignalSubscription]:
    state_rank = func.row_number().over(
        partition_by=SignalSubscriptionStateEvent.subscription_id,
        order_by=(
            SignalSubscriptionStateEvent.effective_at.desc(),
            SignalSubscriptionStateEvent.sequence.desc(),
        ),
    ).label("state_rank")
    ranked_states = (
        select(
            SignalSubscriptionStateEvent.subscription_id,
            SignalSubscriptionStateEvent.user_id,
            SignalSubscriptionStateEvent.subscription_status,
            SignalSubscriptionStateEvent.telegram_delivery_enabled,
            state_rank,
        )
        .where(
            SignalSubscriptionStateEvent.supported_market_id
            == signal_event.supported_market_id,
            SignalSubscriptionStateEvent.signal_preset_id == signal_event.signal_preset_id,
            SignalSubscriptionStateEvent.effective_at <= signal_event.occurred_at,
        )
        .subquery()
    )
    statement = (
        select(
            ranked_states.c.subscription_id,
            ranked_states.c.user_id,
            TelegramConnection.id.label("telegram_connection_id"),
            TelegramConnection.status.label("telegram_connection_status"),
            TelegramConnection.connected_at.label("telegram_connected_at"),
        )
        .outerjoin(
            TelegramConnection,
            TelegramConnection.user_id == ranked_states.c.user_id,
        )
        .where(
            ranked_states.c.state_rank == 1,
            ranked_states.c.subscription_status == "active",
            ranked_states.c.telegram_delivery_enabled.is_(True),
        )
        .order_by(ranked_states.c.subscription_id.asc())
        .limit(limit)
    )
    if after_subscription_id is not None:
        statement = statement.where(
            ranked_states.c.subscription_id > after_subscription_id
        )
    rows = (await session.execute(statement)).all()
    return [
        EligibleSignalSubscription(
            subscription_id=row.subscription_id,
            user_id=row.user_id,
            telegram_connection_id=row.telegram_connection_id,
            telegram_connection_status=row.telegram_connection_status,
            telegram_connected_at=row.telegram_connected_at,
        )
        for row in rows
    ]
