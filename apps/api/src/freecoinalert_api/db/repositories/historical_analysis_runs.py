import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.historical_analysis_run import HistoricalAnalysisRun


async def lock_user_historical_analysis_creation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:user_id AS text), 0))"),
        {"user_id": str(user_id)},
    )


async def count_active_historical_analysis_runs(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(HistoricalAnalysisRun)
            .where(
                HistoricalAnalysisRun.user_id == user_id,
                HistoricalAnalysisRun.status.in_(("queued", "running")),
            )
        )
        or 0
    )


async def get_historical_analysis_run_by_user_and_idempotency_key(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    idempotency_key: uuid.UUID,
) -> HistoricalAnalysisRun | None:
    return await session.scalar(
        select(HistoricalAnalysisRun).where(
            HistoricalAnalysisRun.user_id == user_id,
            HistoricalAnalysisRun.idempotency_key == idempotency_key,
        )
    )


async def get_historical_analysis_run_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
    for_update: bool = False,
) -> HistoricalAnalysisRun | None:
    statement = select(HistoricalAnalysisRun).where(
        HistoricalAnalysisRun.user_id == user_id,
        HistoricalAnalysisRun.id == run_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_historical_analysis_run_by_id(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    for_update: bool = False,
) -> HistoricalAnalysisRun | None:
    statement = select(HistoricalAnalysisRun).where(
        HistoricalAnalysisRun.id == run_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def list_historical_analysis_runs_page_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    status: str | None,
    cursor_created_at: datetime | None,
    cursor_id: uuid.UUID | None,
) -> Sequence[HistoricalAnalysisRun]:
    statement = select(HistoricalAnalysisRun).where(
        HistoricalAnalysisRun.user_id == user_id,
    )
    if status is not None:
        statement = statement.where(HistoricalAnalysisRun.status == status)
    if cursor_created_at is not None and cursor_id is not None:
        statement = statement.where(
            tuple_(HistoricalAnalysisRun.created_at, HistoricalAnalysisRun.id)
            < tuple_(cursor_created_at, cursor_id)
        )
    statement = statement.order_by(
        HistoricalAnalysisRun.created_at.desc(),
        HistoricalAnalysisRun.id.desc(),
    ).limit(limit)
    return (await session.scalars(statement)).all()


async def create_historical_analysis_run(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    supported_market_id: uuid.UUID,
    signal_preset_id: uuid.UUID,
    idempotency_key: uuid.UUID,
    exchange_snapshot: str,
    market_type_snapshot: str,
    symbol_snapshot: str,
    base_asset_snapshot: str,
    quote_asset_snapshot: str,
    preset_code_snapshot: str,
    preset_version_snapshot: int,
    preset_name_snapshot: str,
    strategy_type_snapshot: str,
    timeframe_snapshot: str,
    direction_snapshot: str,
    period_snapshot: int,
    threshold_snapshot: Decimal | None,
    price_input_snapshot: str,
    calculation_version_snapshot: str,
    simulation_version: str,
    assumption_version: str,
    analysis_start: datetime,
    analysis_end: datetime,
    available_at: datetime,
) -> HistoricalAnalysisRun:
    run = HistoricalAnalysisRun(
        user_id=user_id,
        supported_market_id=supported_market_id,
        signal_preset_id=signal_preset_id,
        status="queued",
        idempotency_key=idempotency_key,
        exchange_snapshot=exchange_snapshot,
        market_type_snapshot=market_type_snapshot,
        symbol_snapshot=symbol_snapshot,
        base_asset_snapshot=base_asset_snapshot,
        quote_asset_snapshot=quote_asset_snapshot,
        preset_code_snapshot=preset_code_snapshot,
        preset_version_snapshot=preset_version_snapshot,
        preset_name_snapshot=preset_name_snapshot,
        strategy_type_snapshot=strategy_type_snapshot,
        timeframe_snapshot=timeframe_snapshot,
        direction_snapshot=direction_snapshot,
        period_snapshot=period_snapshot,
        threshold_snapshot=threshold_snapshot,
        price_input_snapshot=price_input_snapshot,
        calculation_version_snapshot=calculation_version_snapshot,
        simulation_version=simulation_version,
        assumption_version=assumption_version,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        progress_stage="queued",
        progress_percent=0,
        attempt_count=0,
        max_attempts=3,
        available_at=available_at,
    )
    session.add(run)
    await session.flush()
    return run
