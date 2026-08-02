from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_event import SignalEvent
from freecoinalert_api.db.models.signal_event_invalidation import SignalEventInvalidation
from freecoinalert_api.db.repositories.signal_feed_stream_events import create_signal_feed_stream_event
from freecoinalert_api.db.repositories.signal_telegram_dispatches import (
    create_signal_telegram_dispatch,
)


async def create_signal_event(
    session: AsyncSession,
    *,
    values: dict[str, object],
) -> SignalEvent | None:
    result = await session.execute(
        insert(SignalEvent)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_signal_events_occurrence")
        .returning(SignalEvent.id)
    )
    event_id = result.scalar_one_or_none()
    if event_id is None:
        return None
    event = await session.get(SignalEvent, event_id)
    if event is None:
        raise RuntimeError("The inserted signal event was not found.")
    await create_signal_feed_stream_event(
        session,
        kind="signal_created",
        signal_event_id=event.id,
    )
    await create_signal_telegram_dispatch(session, signal_event=event)
    return event


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
        .returning(SignalEventInvalidation.id)
    )
    invalidation_id = result.scalar_one_or_none()
    if invalidation_id is None:
        return False
    await create_signal_feed_stream_event(
        session,
        kind="signal_invalidated",
        signal_event_id=signal_event_id,
    )
    return True
