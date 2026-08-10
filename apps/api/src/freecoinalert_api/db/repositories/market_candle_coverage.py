import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from freecoinalert_api.db.models.market_candle_coverage import MarketCandleCoverage


@dataclass(frozen=True, slots=True)
class MarketCandleCoverageValues:
    supported_market_id: uuid.UUID
    timeframe: str
    target_start: datetime
    target_end: datetime
    latest_closed_boundary: datetime
    contiguous_start: datetime | None
    contiguous_end: datetime | None
    available_start: datetime | None
    available_end: datetime | None
    status: str
    missing_range_count: int
    coverage_percent: Decimal
    verified_at: datetime | None
    last_success_at: datetime | None
    last_error_category: str | None


async def upsert_market_candle_coverage(
    session: AsyncSession,
    *,
    values: MarketCandleCoverageValues,
) -> MarketCandleCoverage:
    statement = insert(MarketCandleCoverage).values(
        supported_market_id=values.supported_market_id,
        exchange="binance",
        market_type="spot",
        timeframe=values.timeframe,
        target_start=_utc(values.target_start),
        target_end=_utc(values.target_end),
        latest_closed_boundary=_utc(values.latest_closed_boundary),
        contiguous_start=_optional_utc(values.contiguous_start),
        contiguous_end=_optional_utc(values.contiguous_end),
        available_start=_optional_utc(values.available_start),
        available_end=_optional_utc(values.available_end),
        status=values.status,
        missing_range_count=values.missing_range_count,
        coverage_percent=values.coverage_percent,
        verified_at=_optional_utc(values.verified_at),
        last_success_at=_optional_utc(values.last_success_at),
        last_error_category=values.last_error_category,
    )
    statement = statement.on_conflict_do_update(
        constraint="uq_market_candle_coverage_market_timeframe",
        set_={
            "target_start": statement.excluded.target_start,
            "target_end": statement.excluded.target_end,
            "latest_closed_boundary": statement.excluded.latest_closed_boundary,
            "contiguous_start": statement.excluded.contiguous_start,
            "contiguous_end": statement.excluded.contiguous_end,
            "available_start": statement.excluded.available_start,
            "available_end": statement.excluded.available_end,
            "status": statement.excluded.status,
            "missing_range_count": statement.excluded.missing_range_count,
            "coverage_percent": statement.excluded.coverage_percent,
            "verified_at": statement.excluded.verified_at,
            "last_success_at": statement.excluded.last_success_at,
            "last_error_category": statement.excluded.last_error_category,
            "updated_at": func.now(),
        },
    ).returning(MarketCandleCoverage)
    return (await session.scalars(statement)).one()


async def get_market_candle_coverage(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    for_update: bool = False,
) -> MarketCandleCoverage | None:
    statement = select(MarketCandleCoverage).where(
        MarketCandleCoverage.supported_market_id == supported_market_id,
        MarketCandleCoverage.timeframe == timeframe,
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def list_market_candle_coverage(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID | None = None,
) -> Sequence[MarketCandleCoverage]:
    statement = select(MarketCandleCoverage).order_by(
        MarketCandleCoverage.supported_market_id,
        MarketCandleCoverage.timeframe,
    )
    if supported_market_id is not None:
        statement = statement.where(
            MarketCandleCoverage.supported_market_id == supported_market_id
        )
    return (await session.scalars(statement)).all()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Coverage timestamps must be timezone-aware UTC.")
    return value.astimezone(UTC)


def _optional_utc(value: datetime | None) -> datetime | None:
    return None if value is None else _utc(value)
