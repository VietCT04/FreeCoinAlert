import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import delete, exists, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_event import SignalEvent
from freecoinalert_api.db.models.signal_event_invalidation import SignalEventInvalidation
from freecoinalert_api.db.models.signal_feed_stream_event import SignalFeedStreamEvent
from freecoinalert_api.db.models.signal_subscription import SignalSubscription

SIGNAL_FEED_CHANNEL = "freecoinalert_signal_feed"
SignalFeedStreamKind = Literal["signal_created", "signal_invalidated"]


@dataclass(frozen=True, slots=True)
class SignalFeedStreamRecord:
    stream_event: SignalFeedStreamEvent
    signal_event: SignalEvent
    invalidation: SignalEventInvalidation | None


@dataclass(frozen=True, slots=True)
class SignalFeedHistoryRecord:
    signal_event: SignalEvent
    invalidation: SignalEventInvalidation | None


async def create_signal_feed_stream_event(
    session: AsyncSession,
    *,
    kind: SignalFeedStreamKind,
    signal_event_id: uuid.UUID,
    created_at: datetime | None = None,
) -> SignalFeedStreamEvent:
    values: dict[str, object] = {
        "kind": kind,
        "signal_event_id": signal_event_id,
    }
    if created_at is not None:
        values["created_at"] = created_at
    stream_event = SignalFeedStreamEvent(**values)
    session.add(stream_event)
    await session.flush()
    payload = json.dumps(
        {"sequence": str(stream_event.sequence)},
        separators=(",", ":"),
    )
    await session.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": SIGNAL_FEED_CHANNEL, "payload": payload},
    )
    return stream_event


async def get_latest_stream_sequence(session: AsyncSession) -> int:
    value = await session.scalar(select(func.max(SignalFeedStreamEvent.sequence)))
    return int(value or 0)


async def get_oldest_stream_sequence(session: AsyncSession) -> int | None:
    value = await session.scalar(select(func.min(SignalFeedStreamEvent.sequence)))
    return None if value is None else int(value)


async def get_stream_record(
    session: AsyncSession,
    *,
    sequence: int,
) -> SignalFeedStreamRecord | None:
    statement = (
        select(SignalFeedStreamEvent, SignalEvent, SignalEventInvalidation)
        .join(
            SignalEvent,
            SignalEvent.id == SignalFeedStreamEvent.signal_event_id,
        )
        .outerjoin(
            SignalEventInvalidation,
            SignalEventInvalidation.signal_event_id == SignalEvent.id,
        )
        .where(SignalFeedStreamEvent.sequence == sequence)
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    stream_event, signal_event, invalidation = row
    return SignalFeedStreamRecord(stream_event, signal_event, invalidation)


async def list_visible_history_records(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    cursor: tuple[datetime, uuid.UUID] | None,
    status: Literal["current", "invalidated", "all"],
) -> Sequence[SignalFeedHistoryRecord]:
    visibility = exists(
        select(SignalSubscription.id).where(
            SignalSubscription.user_id == user_id,
            SignalSubscription.supported_market_id == SignalEvent.supported_market_id,
            SignalSubscription.signal_preset_id == SignalEvent.signal_preset_id,
            SignalSubscription.status.in_(("active", "disabled")),
        )
    )
    statement = (
        select(SignalEvent, SignalEventInvalidation)
        .outerjoin(
            SignalEventInvalidation,
            SignalEventInvalidation.signal_event_id == SignalEvent.id,
        )
        .where(visibility)
    )
    if status == "current":
        statement = statement.where(SignalEventInvalidation.id.is_(None))
    elif status == "invalidated":
        statement = statement.where(SignalEventInvalidation.id.is_not(None))
    if cursor is not None:
        occurred_at, event_id = cursor
        statement = statement.where(
            (SignalEvent.occurred_at < occurred_at)
            | ((SignalEvent.occurred_at == occurred_at) & (SignalEvent.id < event_id))
        )
    statement = statement.order_by(
        SignalEvent.occurred_at.desc(),
        SignalEvent.id.desc(),
    ).limit(limit)
    rows = (await session.execute(statement)).all()
    return [SignalFeedHistoryRecord(*row) for row in rows]


async def list_active_replay_records(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    after_sequence: int,
    through_sequence: int,
    limit: int,
) -> Sequence[SignalFeedStreamRecord]:
    visibility = exists(
        select(SignalSubscription.id).where(
            SignalSubscription.user_id == user_id,
            SignalSubscription.supported_market_id == SignalEvent.supported_market_id,
            SignalSubscription.signal_preset_id == SignalEvent.signal_preset_id,
            SignalSubscription.status == "active",
        )
    )
    statement = (
        select(SignalFeedStreamEvent, SignalEvent, SignalEventInvalidation)
        .join(
            SignalEvent,
            SignalEvent.id == SignalFeedStreamEvent.signal_event_id,
        )
        .outerjoin(
            SignalEventInvalidation,
            SignalEventInvalidation.signal_event_id == SignalEvent.id,
        )
        .where(
            SignalFeedStreamEvent.sequence > after_sequence,
            SignalFeedStreamEvent.sequence <= through_sequence,
            visibility,
        )
        .order_by(SignalFeedStreamEvent.sequence.asc())
        .limit(limit)
    )
    rows = (await session.execute(statement)).all()
    return [SignalFeedStreamRecord(*row) for row in rows]


async def get_active_replay_record(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    sequence: int,
) -> SignalFeedStreamRecord | None:
    records = await list_active_replay_records(
        session,
        user_id=user_id,
        after_sequence=sequence - 1,
        through_sequence=sequence,
        limit=1,
    )
    return records[0] if records and records[0].stream_event.sequence == sequence else None


async def delete_old_stream_events(
    session: AsyncSession,
    *,
    cutoff: datetime,
    limit: int = 10_000,
) -> int:
    candidates = (
        select(SignalFeedStreamEvent.sequence)
        .where(SignalFeedStreamEvent.created_at < cutoff)
        .order_by(SignalFeedStreamEvent.created_at.asc(), SignalFeedStreamEvent.sequence.asc())
        .limit(limit)
        .subquery()
    )
    result = await session.execute(
        delete(SignalFeedStreamEvent).where(
            SignalFeedStreamEvent.sequence.in_(select(candidates.c.sequence))
        )
    )
    return result.rowcount or 0
