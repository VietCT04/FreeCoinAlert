"""Bounded canonical-candle coverage reads for Historical Analysis."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.market_candle import MarketCandle


CoverageStatus = Literal["ready", "partial", "unavailable"]


@dataclass(frozen=True, slots=True)
class HistoricalAnalysisCoverage:
    status: CoverageStatus
    raw_contiguous_start: datetime | None
    raw_contiguous_end: datetime | None
    observed_candle_count: int
    expected_candle_count: int
    verified_at: datetime

    @property
    def is_usable(self) -> bool:
        return self.status == "ready"


async def get_historical_analysis_coverage(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    start_open_time: datetime,
    end_open_time: datetime,
    timeframe_delta: timedelta,
    expected_candle_count: int,
) -> HistoricalAnalysisCoverage:
    """Resolve exact requested coverage without materializing candle rows.

    This is intentionally a read boundary. Coverage maintenance and provider
    acquisition belong to the market-data background processes; this query
    only inspects current, complete canonical rows already in PostgreSQL.
    """

    stats = await session.execute(
        select(
            func.count(MarketCandle.id),
            func.min(MarketCandle.open_time),
            func.max(MarketCandle.close_time),
        ).where(
            MarketCandle.supported_market_id == supported_market_id,
            MarketCandle.timeframe == timeframe,
            MarketCandle.status == "complete",
            MarketCandle.is_current.is_(True),
            MarketCandle.open_time >= start_open_time,
            MarketCandle.open_time < end_open_time,
        )
    )
    observed_count, first_open_time, last_close_time = stats.one()
    observed_count = int(observed_count or 0)

    gap_query = select(
        MarketCandle.open_time.label("open_time"),
        func.lag(MarketCandle.open_time)
        .over(order_by=MarketCandle.open_time)
        .label("previous_open_time"),
    ).where(
        MarketCandle.supported_market_id == supported_market_id,
        MarketCandle.timeframe == timeframe,
        MarketCandle.status == "complete",
        MarketCandle.is_current.is_(True),
        MarketCandle.open_time >= start_open_time,
        MarketCandle.open_time < end_open_time,
    ).subquery()
    first_gap = await session.scalar(
        select(gap_query.c.open_time)
        .where(
            gap_query.c.previous_open_time.is_not(None),
            gap_query.c.open_time - gap_query.c.previous_open_time != timeframe_delta,
        )
        .limit(1)
    )

    complete = (
        observed_count == expected_candle_count
        and first_open_time == start_open_time
        and last_close_time == end_open_time
        and first_gap is None
    )
    verified_at = datetime.now(UTC)
    if complete:
        return HistoricalAnalysisCoverage(
            status="ready",
            raw_contiguous_start=start_open_time,
            raw_contiguous_end=end_open_time,
            observed_candle_count=observed_count,
            expected_candle_count=expected_candle_count,
            verified_at=verified_at,
        )

    return HistoricalAnalysisCoverage(
        status="unavailable" if observed_count == 0 else "partial",
        raw_contiguous_start=None,
        raw_contiguous_end=None,
        observed_candle_count=observed_count,
        expected_candle_count=expected_candle_count,
        verified_at=verified_at,
    )
