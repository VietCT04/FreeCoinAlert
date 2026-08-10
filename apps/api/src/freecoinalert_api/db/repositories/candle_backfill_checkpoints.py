from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from freecoinalert_api.db.models.candle_backfill_checkpoint import CandleBackfillCheckpoint


BACKFILL_ADVISORY_LOCK_KEY = "freecoinalert:candle-backfill:binance:spot"


async def try_acquire_backfill_lock(connection: AsyncConnection) -> bool:
    return bool(
        await connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": BACKFILL_ADVISORY_LOCK_KEY},
        )
    )


async def release_backfill_lock(connection: AsyncConnection) -> None:
    await connection.scalar(
        text("SELECT pg_advisory_unlock(hashtext(:lock_key))"),
        {"lock_key": BACKFILL_ADVISORY_LOCK_KEY},
    )


async def get_checkpoint(
    session: AsyncSession,
    *,
    archive_key: str,
    for_update: bool = False,
) -> CandleBackfillCheckpoint | None:
    statement = select(CandleBackfillCheckpoint).where(
        CandleBackfillCheckpoint.archive_key == archive_key
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def ensure_checkpoint(
    session: AsyncSession,
    *,
    supported_market_id: UUID,
    archive_granularity: str,
    period_start: datetime,
    period_end: datetime,
    archive_key: str,
) -> CandleBackfillCheckpoint:
    checkpoint = await get_checkpoint(session, archive_key=archive_key, for_update=True)
    if checkpoint is not None:
        return checkpoint

    checkpoint = CandleBackfillCheckpoint(
        supported_market_id=supported_market_id,
        exchange="binance",
        market_type="spot",
        timeframe="1m",
        archive_granularity=archive_granularity,
        period_start=period_start.astimezone(UTC),
        period_end=period_end.astimezone(UTC),
        archive_key=archive_key,
        checksum_sha256=None,
        status="pending",
        next_open_time=period_start.astimezone(UTC),
        attempt_count=0,
        last_error_category=None,
        started_at=None,
        completed_at=None,
    )
    session.add(checkpoint)
    await session.flush()
    return checkpoint


async def start_checkpoint_attempt(
    session: AsyncSession,
    *,
    checkpoint: CandleBackfillCheckpoint,
    started_at: datetime,
) -> None:
    if checkpoint.status == "complete":
        return
    checkpoint.status = "processing"
    checkpoint.attempt_count += 1
    checkpoint.last_error_category = None
    checkpoint.started_at = started_at.astimezone(UTC)
    checkpoint.completed_at = None
    await session.flush()


async def record_verified_checksum(
    session: AsyncSession,
    *,
    checkpoint: CandleBackfillCheckpoint,
    checksum_sha256: str,
) -> None:
    checkpoint.checksum_sha256 = checksum_sha256
    checkpoint.updated_at = datetime.now(UTC)
    await session.flush()


async def advance_checkpoint(
    session: AsyncSession,
    *,
    checkpoint: CandleBackfillCheckpoint,
    next_open_time: datetime,
) -> None:
    normalized_next = next_open_time.astimezone(UTC)
    if normalized_next < checkpoint.next_open_time or normalized_next > checkpoint.period_end:
        raise ValueError("Checkpoint progress must move within the archive period.")
    checkpoint.next_open_time = normalized_next
    checkpoint.updated_at = datetime.now(UTC)
    await session.flush()


async def mark_checkpoint_complete(
    session: AsyncSession,
    *,
    checkpoint: CandleBackfillCheckpoint,
    completed_at: datetime,
) -> None:
    if checkpoint.next_open_time != checkpoint.period_end:
        raise ValueError("An archive checkpoint cannot complete before its final chunk.")
    checkpoint.status = "complete"
    checkpoint.last_error_category = None
    checkpoint.completed_at = completed_at.astimezone(UTC)
    checkpoint.updated_at = completed_at.astimezone(UTC)
    await session.flush()


async def mark_checkpoint_failed(
    session: AsyncSession,
    *,
    checkpoint: CandleBackfillCheckpoint,
    category: str,
) -> None:
    checkpoint.status = "failed"
    checkpoint.last_error_category = category
    checkpoint.completed_at = None
    checkpoint.updated_at = datetime.now(UTC)
    await session.flush()
