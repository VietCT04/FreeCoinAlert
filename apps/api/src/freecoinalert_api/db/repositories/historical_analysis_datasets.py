import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.historical_analysis_dataset import (
    HistoricalAnalysisDataset,
)
from freecoinalert_api.db.models.historical_analysis_dataset_candle import (
    HistoricalAnalysisDatasetCandle,
)
from freecoinalert_api.db.models.market_candle import MarketCandle


async def get_historical_analysis_dataset_for_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    for_update: bool = False,
) -> HistoricalAnalysisDataset | None:
    statement = select(HistoricalAnalysisDataset).where(
        HistoricalAnalysisDataset.run_id == run_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_historical_analysis_dataset(
    session: AsyncSession,
    *,
    dataset_id: uuid.UUID,
    for_update: bool = False,
) -> HistoricalAnalysisDataset | None:
    statement = select(HistoricalAnalysisDataset).where(
        HistoricalAnalysisDataset.id == dataset_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def list_historical_analysis_dataset_candles(
    session: AsyncSession,
    *,
    dataset_id: uuid.UUID,
) -> Sequence[HistoricalAnalysisDatasetCandle]:
    statement = select(HistoricalAnalysisDatasetCandle).where(
        HistoricalAnalysisDatasetCandle.dataset_id == dataset_id,
    ).order_by(HistoricalAnalysisDatasetCandle.position.asc())
    return (await session.scalars(statement)).all()


async def list_current_candles_for_historical_dataset(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    start_open_time: datetime,
    end_open_time: datetime,
    limit: int,
) -> Sequence[MarketCandle]:
    statement = (
        select(MarketCandle)
        .where(
            MarketCandle.supported_market_id == supported_market_id,
            MarketCandle.timeframe == timeframe,
            MarketCandle.is_current.is_(True),
            MarketCandle.open_time >= start_open_time,
            MarketCandle.open_time < end_open_time,
        )
        .order_by(MarketCandle.open_time.asc())
        .limit(limit)
        .with_for_update(read=True)
    )
    return (await session.scalars(statement)).all()


async def get_market_candles_for_historical_dataset_share(
    session: AsyncSession,
    *,
    candle_ids: Sequence[uuid.UUID],
) -> Sequence[MarketCandle]:
    if not candle_ids:
        return []
    statement = (
        select(MarketCandle)
        .where(MarketCandle.id.in_(candle_ids))
        .with_for_update(read=True)
    )
    return (await session.scalars(statement)).all()


async def create_historical_analysis_dataset(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    supported_market_id: uuid.UUID,
    signal_preset_id: uuid.UUID,
    status: str,
    failure_code: str | None,
    timeframe: str,
    analysis_start: datetime,
    analysis_end: datetime,
    warmup_start: datetime,
    required_warmup_candles: int,
    warmup_candle_count: int,
    analysis_candle_count: int,
    total_candle_count: int,
    first_open_time: datetime,
    last_close_time: datetime,
    manifest_fingerprint: str,
    prepared_at: datetime,
    stale_at: datetime | None = None,
) -> HistoricalAnalysisDataset:
    dataset = HistoricalAnalysisDataset(
        run_id=run_id,
        supported_market_id=supported_market_id,
        signal_preset_id=signal_preset_id,
        status=status,
        failure_code=failure_code,
        timeframe=timeframe,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        warmup_start=warmup_start,
        required_warmup_candles=required_warmup_candles,
        warmup_candle_count=warmup_candle_count,
        analysis_candle_count=analysis_candle_count,
        total_candle_count=total_candle_count,
        first_open_time=first_open_time,
        last_close_time=last_close_time,
        manifest_fingerprint=manifest_fingerprint,
        prepared_at=prepared_at,
        stale_at=stale_at,
    )
    session.add(dataset)
    await session.flush()
    return dataset


async def create_historical_analysis_dataset_candles(
    session: AsyncSession,
    *,
    snapshots: Sequence[HistoricalAnalysisDatasetCandle],
) -> None:
    session.add_all(snapshots)
    await session.flush()
