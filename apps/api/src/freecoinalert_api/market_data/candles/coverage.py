"""Canonical candle coverage state and source-neutral planning contracts.

Archive/checkpoint acquisition (#151) and REST reconciliation (#152) provide
adapters to these contracts. This module owns neither provider implementation.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.market_candle_coverage import MarketCandleCoverage
from freecoinalert_api.db.repositories.market_candle_coverage import (
    MarketCandleCoverageValues,
    get_market_candle_coverage,
    list_market_candle_coverage,
    upsert_market_candle_coverage,
)
from freecoinalert_api.db.repositories.market_candles import (
    CandleCoverageStatistics,
    MissingCandleRange,
    find_missing_candle_ranges,
    get_complete_candle_coverage,
    get_newest_contiguous_candle_range,
)
from freecoinalert_api.market_data.candles.constants import (
    MAX_CANDLE_BOOTSTRAP_DAYS,
    MIN_CANDLE_BOOTSTRAP_DAYS,
)


TIMEFRAME_DELTAS = {
    "1m": timedelta(minutes=1),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}


@dataclass(frozen=True, slots=True)
class CoverageTarget:
    supported_market_id: UUID
    symbol: str
    timeframe: str
    target_start: datetime
    target_end: datetime
    latest_closed_boundary: datetime
    target_days: int


@dataclass(frozen=True, slots=True)
class PlannedCoverageWork:
    source: str
    range: MissingCandleRange


@dataclass(frozen=True, slots=True)
class ArchiveCoveragePlanningResult:
    work_ranges: tuple[MissingCandleRange, ...]
    unresolved_ranges: tuple[MissingCandleRange, ...]


@dataclass(frozen=True, slots=True)
class RestCoveragePlanningResult:
    work_ranges: tuple[MissingCandleRange, ...]
    unresolved_ranges: tuple[MissingCandleRange, ...]


class ArchiveCoverageSource(Protocol):
    """Adapter owned by #151 for archive/checkpoint-backed work selection."""

    async def plan_missing_ranges(
        self,
        *,
        target: CoverageTarget,
        missing_ranges: Sequence[MissingCandleRange],
    ) -> ArchiveCoveragePlanningResult: ...


class RestCoverageSource(Protocol):
    """Adapter owned by #152 for bounded REST repair work selection."""

    async def plan_missing_ranges(
        self,
        *,
        target: CoverageTarget,
        missing_ranges: Sequence[MissingCandleRange],
    ) -> RestCoveragePlanningResult: ...


@dataclass(frozen=True, slots=True)
class CoveragePlan:
    target: CoverageTarget
    statistics: CandleCoverageStatistics
    missing_ranges: tuple[MissingCandleRange, ...]
    archive_work: tuple[PlannedCoverageWork, ...]
    rest_work: tuple[PlannedCoverageWork, ...]
    unresolved_ranges: tuple[MissingCandleRange, ...]

    @property
    def is_complete(self) -> bool:
        return self.statistics.is_complete


@dataclass(frozen=True, slots=True)
class CoverageResolution:
    raw_contiguous_start: datetime | None
    raw_contiguous_end: datetime | None
    warmup_candles: int
    first_selectable_analysis_start: datetime | None
    latest_selectable_analysis_end: datetime | None
    available_analysis_days: int
    verified_at: datetime | None
    status: str


def build_coverage_target(
    *,
    supported_market_id: UUID,
    symbol: str,
    timeframe: str,
    now: datetime,
    target_days: int,
) -> CoverageTarget:
    _validate_timeframe(timeframe)
    _validate_target_days(target_days)
    latest_closed_boundary = latest_closed_1m_boundary(now)
    target_end = align_boundary(latest_closed_boundary, timeframe)
    return CoverageTarget(
        supported_market_id=supported_market_id,
        symbol=symbol,
        timeframe=timeframe,
        target_start=target_end - timedelta(days=target_days),
        target_end=target_end,
        latest_closed_boundary=latest_closed_boundary,
        target_days=target_days,
    )


async def plan_coverage(
    session: AsyncSession,
    *,
    target: CoverageTarget,
    archive_source: ArchiveCoverageSource | None = None,
    rest_source: RestCoverageSource | None = None,
) -> CoveragePlan:
    """Plan only missing canonical ranges, newest contiguous work first.

    A complete canonical range returns before either source adapter is called,
    which is the no-redownload guarantee for later scans.
    """

    statistics = await get_complete_candle_coverage(
        session,
        supported_market_id=target.supported_market_id,
        timeframe=target.timeframe,
        start_open_time=target.target_start,
        end_open_time=target.target_end,
    )
    missing = tuple(
        sorted(
            await find_missing_candle_ranges(
                session,
                supported_market_id=target.supported_market_id,
                timeframe=target.timeframe,
                start_open_time=target.target_start,
                end_open_time=target.target_end,
            ),
            key=lambda item: (item.end_open_time, item.start_open_time),
            reverse=True,
        )
    )
    if statistics.is_complete:
        return CoveragePlan(
            target=target,
            statistics=statistics,
            missing_ranges=(),
            archive_work=(),
            rest_work=(),
            unresolved_ranges=(),
        )

    archive_result = ArchiveCoveragePlanningResult((), missing)
    if archive_source is not None and missing:
        archive_result = await archive_source.plan_missing_ranges(
            target=target,
            missing_ranges=missing,
        )
    unresolved_after_archive = _ordered_ranges(archive_result.unresolved_ranges)

    rest_result = RestCoveragePlanningResult((), unresolved_after_archive)
    if rest_source is not None and unresolved_after_archive:
        rest_result = await rest_source.plan_missing_ranges(
            target=target,
            missing_ranges=unresolved_after_archive,
        )

    return CoveragePlan(
        target=target,
        statistics=statistics,
        missing_ranges=missing,
        archive_work=tuple(
            PlannedCoverageWork(source="archive", range=gap)
            for gap in _ordered_ranges(archive_result.work_ranges)
        ),
        rest_work=tuple(
            PlannedCoverageWork(source="rest", range=gap)
            for gap in _ordered_ranges(rest_result.work_ranges)
        ),
        unresolved_ranges=_ordered_ranges(rest_result.unresolved_ranges),
    )


async def persist_coverage_plan(
    session: AsyncSession,
    *,
    plan: CoveragePlan,
    verified_at: datetime,
    last_success_at: datetime | None = None,
    last_error_category: str | None = None,
) -> MarketCandleCoverage:
    """Persist a derived state snapshot after canonical verification."""

    contiguous_range = await get_newest_contiguous_candle_range(
        session,
        supported_market_id=plan.target.supported_market_id,
        timeframe=plan.target.timeframe,
        start_open_time=plan.target.target_start,
        end_open_time=plan.target.target_end,
    )
    contiguous_start, contiguous_end = (
        (None, None) if contiguous_range is None else contiguous_range
    )
    if plan.is_complete:
        status = "ready"
    elif last_error_category is not None:
        status = "degraded"
    else:
        status = "backfilling"
    coverage_percent = _coverage_percent(
        complete_count=plan.statistics.complete_count,
        expected_count=plan.statistics.expected_count,
    )
    return await upsert_market_candle_coverage(
        session,
        values=MarketCandleCoverageValues(
            supported_market_id=plan.target.supported_market_id,
            timeframe=plan.target.timeframe,
            target_start=plan.target.target_start,
            target_end=plan.target.target_end,
            latest_closed_boundary=plan.target.latest_closed_boundary,
            contiguous_start=contiguous_start,
            contiguous_end=contiguous_end,
            available_start=contiguous_start,
            available_end=contiguous_end,
            status=status,
            missing_range_count=len(plan.missing_ranges),
            coverage_percent=coverage_percent,
            verified_at=_utc(verified_at),
            last_success_at=(None if last_success_at is None else _utc(last_success_at)),
            last_error_category=last_error_category,
        ),
    )


async def refresh_coverage_after_retention(
    session: AsyncSession,
    *,
    now: datetime,
) -> None:
    """Recalculate persisted summaries after retention removes old rows."""

    for state in await list_market_candle_coverage(session):
        target_days = (state.target_end - state.target_start).days
        target = build_coverage_target(
            supported_market_id=state.supported_market_id,
            symbol="",
            timeframe=state.timeframe,
            now=now,
            target_days=target_days,
        )
        plan = await plan_coverage(session, target=target)
        await persist_coverage_plan(
            session,
            plan=plan,
            verified_at=now,
            last_success_at=state.last_success_at,
            last_error_category=state.last_error_category,
        )


def resolve_coverage_for_analysis(
    coverage: MarketCandleCoverage,
    *,
    required_warmup_candles: int,
) -> CoverageResolution:
    """Resolve the server-owned warm-up boundary for #154/#155 consumers."""

    if required_warmup_candles < 0:
        raise ValueError("Required warm-up candles cannot be negative.")
    _validate_timeframe(coverage.timeframe)
    available_start = coverage.available_start or coverage.contiguous_start
    available_end = coverage.available_end or coverage.contiguous_end
    first_selectable = None
    available_days = 0
    if available_start is not None and available_end is not None:
        first_selectable = available_start + required_warmup_candles * TIMEFRAME_DELTAS[
            coverage.timeframe
        ]
        if first_selectable >= available_end:
            first_selectable = None
        else:
            available_days = max(
                0,
                int((available_end - first_selectable) / timedelta(days=1)),
            )
    return CoverageResolution(
        raw_contiguous_start=available_start,
        raw_contiguous_end=available_end,
        warmup_candles=required_warmup_candles,
        first_selectable_analysis_start=first_selectable,
        latest_selectable_analysis_end=available_end,
        available_analysis_days=available_days,
        verified_at=coverage.verified_at,
        status=coverage.status,
    )


async def get_analysis_coverage_resolution(
    session: AsyncSession,
    *,
    supported_market_id: UUID,
    timeframe: str,
    required_warmup_candles: int,
) -> CoverageResolution | None:
    """Read the safe internal coverage contract used by #154/#155."""

    coverage = await get_market_candle_coverage(
        session,
        supported_market_id=supported_market_id,
        timeframe=timeframe,
    )
    if coverage is None:
        return None
    return resolve_coverage_for_analysis(
        coverage,
        required_warmup_candles=required_warmup_candles,
    )


def latest_closed_1m_boundary(now: datetime) -> datetime:
    now = _utc(now)
    return now.replace(second=0, microsecond=0)


def align_boundary(boundary: datetime, timeframe: str) -> datetime:
    _validate_timeframe(timeframe)
    boundary = _utc(boundary)
    if timeframe == "1m":
        return boundary
    hour = boundary.hour
    if timeframe == "4h":
        hour -= hour % 4
    return boundary.replace(hour=hour, minute=0)


def _coverage_percent(*, complete_count: int, expected_count: int) -> Decimal:
    if expected_count <= 0:
        return Decimal("0")
    return (
        (Decimal(complete_count) * Decimal("100") / Decimal(expected_count))
        .quantize(Decimal("0.001"), rounding=ROUND_DOWN)
    )


def _ordered_ranges(
    ranges: Sequence[MissingCandleRange],
) -> tuple[MissingCandleRange, ...]:
    return tuple(
        sorted(
            ranges,
            key=lambda item: (item.end_open_time, item.start_open_time),
            reverse=True,
        )
    )


def _validate_timeframe(timeframe: str) -> None:
    if timeframe not in TIMEFRAME_DELTAS:
        raise ValueError("Unsupported candle timeframe.")


def _validate_target_days(target_days: int) -> None:
    if not MIN_CANDLE_BOOTSTRAP_DAYS <= target_days <= MAX_CANDLE_BOOTSTRAP_DAYS:
        raise ValueError(
            f"Candle target days must be between {MIN_CANDLE_BOOTSTRAP_DAYS} "
            f"and {MAX_CANDLE_BOOTSTRAP_DAYS}."
        )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Coverage timestamps must be timezone-aware UTC.")
    return value.astimezone(UTC)
