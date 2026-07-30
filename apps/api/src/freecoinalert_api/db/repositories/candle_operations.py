from datetime import datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from freecoinalert_api.db.models.candle_symbol_state import CandleSymbolState
from freecoinalert_api.db.models.candle_sync_run import CandleSyncRun


async def start_candle_sync_run(
    session: AsyncSession,
    *,
    kind: str,
    requested_start: datetime,
    requested_end: datetime,
    started_at: datetime,
) -> CandleSyncRun:
    run = CandleSyncRun(
        kind=kind,
        status="running",
        requested_start=requested_start,
        requested_end=requested_end,
        current_market_id=None,
        next_open_time=requested_start,
        source_rows_written=0,
        source_rows_unchanged=0,
        source_rows_corrected=0,
        derived_rows_written=0,
        unresolved_gap_count=0,
        failure_code=None,
        started_at=started_at,
        finished_at=None,
    )
    session.add(run)
    await session.flush()
    return run


async def update_candle_sync_run(
    session: AsyncSession,
    *,
    run: CandleSyncRun,
    current_market_id: UUID | None,
    next_open_time: datetime | None,
    source_rows_written: int,
    source_rows_unchanged: int,
    source_rows_corrected: int,
    derived_rows_written: int,
    unresolved_gap_count: int,
) -> None:
    run.current_market_id = current_market_id
    run.next_open_time = next_open_time
    run.source_rows_written = source_rows_written
    run.source_rows_unchanged = source_rows_unchanged
    run.source_rows_corrected = source_rows_corrected
    run.derived_rows_written = derived_rows_written
    run.unresolved_gap_count = unresolved_gap_count
    await session.flush()


async def finish_candle_sync_run(
    session: AsyncSession,
    *,
    run: CandleSyncRun,
    status: str,
    finished_at: datetime,
    failure_code: str | None = None,
) -> None:
    run.status = status
    run.failure_code = failure_code
    run.finished_at = finished_at
    await session.flush()


async def upsert_candle_symbol_state(
    session: AsyncSession,
    *,
    supported_market_id: UUID,
    status: str,
    latest_complete_1m_open_time: datetime | None,
    latest_complete_1h_open_time: datetime | None,
    latest_complete_4h_open_time: datetime | None,
    last_websocket_received_at: datetime | None,
    last_reconciled_through: datetime | None,
    unresolved_gap_count: int,
    status_reason: str | None,
) -> None:
    statement = insert(CandleSymbolState).values(
        supported_market_id=supported_market_id,
        status=status,
        latest_complete_1m_open_time=latest_complete_1m_open_time,
        latest_complete_1h_open_time=latest_complete_1h_open_time,
        latest_complete_4h_open_time=latest_complete_4h_open_time,
        last_websocket_received_at=last_websocket_received_at,
        last_reconciled_through=last_reconciled_through,
        unresolved_gap_count=unresolved_gap_count,
        status_reason=status_reason,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[CandleSymbolState.supported_market_id],
        set_={
            "status": statement.excluded.status,
            "latest_complete_1m_open_time": statement.excluded.latest_complete_1m_open_time,
            "latest_complete_1h_open_time": statement.excluded.latest_complete_1h_open_time,
            "latest_complete_4h_open_time": statement.excluded.latest_complete_4h_open_time,
            "last_websocket_received_at": statement.excluded.last_websocket_received_at,
            "last_reconciled_through": statement.excluded.last_reconciled_through,
            "unresolved_gap_count": statement.excluded.unresolved_gap_count,
            "status_reason": statement.excluded.status_reason,
            "updated_at": func.now(),
        },
    )
    await session.execute(statement)
