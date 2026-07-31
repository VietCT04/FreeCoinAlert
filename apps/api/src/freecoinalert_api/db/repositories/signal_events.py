from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_event import SignalEvent
from freecoinalert_api.db.models.signal_event_invalidation import SignalEventInvalidation


async def create_signal_event(
    session: AsyncSession,
    *,
    values: dict[str, object],
) -> bool:
    result = await session.execute(
        insert(SignalEvent).values(**values).on_conflict_do_nothing(
            constraint="uq_signal_events_occurrence"
        )
    )
    return bool(result.rowcount)


async def list_signal_events_for_market_preset_range(
    session: AsyncSession,
    *,
    supported_market_id: UUID,
    signal_preset_id: UUID,
    start_open_time: datetime,
    end_open_time: datetime,
) -> Sequence[SignalEvent]:
    statement = select(SignalEvent).where(
        SignalEvent.supported_market_id == supported_market_id,
        SignalEvent.signal_preset_id == signal_preset_id,
        SignalEvent.candle_open_time >= start_open_time,
        SignalEvent.candle_open_time < end_open_time,
    )
    return (await session.scalars(statement.order_by(SignalEvent.candle_open_time))).all()


async def create_signal_event_invalidation(
    session: AsyncSession,
    *,
    signal_event_id: UUID,
    reason: str,
    replacement_candle_id: UUID | None,
    replacement_candle_revision: int | None,
) -> bool:
    result = await session.execute(
        insert(SignalEventInvalidation)
        .values(
            signal_event_id=signal_event_id,
            reason=reason,
            replacement_candle_id=replacement_candle_id,
            replacement_candle_revision=replacement_candle_revision,
        )
        .on_conflict_do_nothing(constraint="uq_signal_event_invalidations_event")
    )
    return bool(result.rowcount)
