import hashlib
import json
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.historical_analysis_dataset import (
    HistoricalAnalysisDataset,
)
from freecoinalert_api.db.models.historical_analysis_dataset_candle import (
    HistoricalAnalysisDatasetCandle,
)
from freecoinalert_api.db.models.historical_analysis_run import HistoricalAnalysisRun
from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.repositories.historical_analysis_datasets import (
    create_historical_analysis_dataset,
    create_historical_analysis_dataset_candles,
    get_historical_analysis_dataset,
    get_historical_analysis_dataset_for_run,
    get_market_candles_for_historical_dataset_share,
    list_current_candles_for_historical_dataset,
    list_historical_analysis_dataset_candles,
)
from freecoinalert_api.db.repositories.historical_analysis_runs import (
    get_historical_analysis_run_by_id,
)
from freecoinalert_api.historical_analysis.service import (
    REQUIRED_WARMUP_CANDLES,
    SUPPORTED_CALCULATION_VERSIONS,
    TIMEFRAME_HOURS,
)
from freecoinalert_api.market_data.catalog import utc_now


logger = logging.getLogger(__name__)

MAX_HISTORICAL_DATASET_CANDLES = 2_500
FINGERPRINT_SCHEMA_VERSION = "historical_dataset_fingerprint_v1"
TIMEFRAME_DELTAS = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}
EXPECTED_SOURCE_CANDLE_COUNTS = {"1h": 60, "4h": 240}

HistoricalDatasetFailureCode = Literal[
    "historical_dataset_insufficient_warmup",
    "historical_dataset_gap_detected",
    "historical_dataset_incomplete",
    "historical_dataset_invalid",
    "historical_dataset_correction_race",
    "historical_dataset_too_large",
    "historical_dataset_unavailable",
    "historical_dataset_stale",
]


@dataclass(frozen=True, slots=True)
class HistoricalDatasetBounds:
    timeframe: str
    timeframe_delta: timedelta
    analysis_start: datetime
    analysis_end: datetime
    warmup_start: datetime
    required_warmup_candles: int
    expected_analysis_candles: int
    expected_total_candles: int


@dataclass(frozen=True, slots=True)
class ManifestCandle:
    candle_id: uuid.UUID
    candle_revision: int
    is_warmup: bool
    timeframe: str
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    base_volume: Decimal
    quote_volume: Decimal
    trade_count: int
    source_kind: str
    source_candle_count: int
    expected_source_candle_count: int
    source_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class HistoricalAnalysisDatasetPreparationResult:
    dataset: HistoricalAnalysisDataset | None
    failure_code: HistoricalDatasetFailureCode | None
    replayed: bool


@dataclass(frozen=True, slots=True)
class HistoricalAnalysisDatasetValidationResult:
    dataset: HistoricalAnalysisDataset | None
    stale: bool
    failure_code: HistoricalDatasetFailureCode | None


async def prepare_historical_analysis_dataset(
    session: AsyncSession,
    run_id: uuid.UUID,
) -> HistoricalAnalysisDatasetPreparationResult:
    """Validate canonical coverage and persist one immutable dataset snapshot."""

    try:
        run = await get_historical_analysis_run_by_id(
            session,
            run_id=run_id,
            for_update=True,
        )
        if run is None:
            await session.rollback()
            return HistoricalAnalysisDatasetPreparationResult(
                dataset=None,
                failure_code="historical_dataset_unavailable",
                replayed=False,
            )

        existing = await get_historical_analysis_dataset_for_run(
            session,
            run_id=run_id,
            for_update=True,
        )
        if existing is not None:
            await session.commit()
            _log_dataset_replayed(run, existing)
            return HistoricalAnalysisDatasetPreparationResult(
                dataset=existing,
                failure_code=existing.failure_code,
                replayed=True,
            )

        if run.status not in {"queued", "running"} or run.cancellation_requested_at is not None:
            await session.rollback()
            return HistoricalAnalysisDatasetPreparationResult(
                dataset=None,
                failure_code="historical_dataset_unavailable",
                replayed=False,
            )

        try:
            bounds = resolve_historical_dataset_bounds(run)
        except ValueError:
            await session.rollback()
            return HistoricalAnalysisDatasetPreparationResult(
                dataset=None,
                failure_code="historical_dataset_invalid",
                replayed=False,
            )

        if bounds.expected_total_candles > MAX_HISTORICAL_DATASET_CANDLES:
            dataset = await _create_failed_dataset(
                session,
                run=run,
                bounds=bounds,
                failure_code="historical_dataset_too_large",
                candles=(),
            )
            await session.commit()
            _log_dataset_rejected(run, dataset, "historical_dataset_too_large")
            return HistoricalAnalysisDatasetPreparationResult(
                dataset=dataset,
                failure_code="historical_dataset_too_large",
                replayed=False,
            )

        candles = await list_current_candles_for_historical_dataset(
            session,
            supported_market_id=run.supported_market_id,
            timeframe=bounds.timeframe,
            start_open_time=bounds.warmup_start,
            end_open_time=bounds.analysis_end,
            limit=MAX_HISTORICAL_DATASET_CANDLES + 1,
        )
        failure_code = validate_historical_dataset_coverage(
            run,
            bounds,
            candles,
        )
        if failure_code is not None:
            dataset = await _create_failed_dataset(
                session,
                run=run,
                bounds=bounds,
                failure_code=failure_code,
                candles=candles,
            )
            await session.commit()
            _log_dataset_rejected(run, dataset, failure_code)
            return HistoricalAnalysisDatasetPreparationResult(
                dataset=dataset,
                failure_code=failure_code,
                replayed=False,
            )

        manifest_candles = tuple(
            manifest_candle_from_market(candle, bounds=bounds)
            for candle in candles
        )
        manifest_fingerprint = calculate_historical_dataset_fingerprint(
            run=run,
            bounds=bounds,
            candles=manifest_candles,
        )
        dataset = await create_historical_analysis_dataset(
            session,
            run_id=run.id,
            supported_market_id=run.supported_market_id,
            signal_preset_id=run.signal_preset_id,
            status="ready",
            failure_code=None,
            timeframe=bounds.timeframe,
            analysis_start=bounds.analysis_start,
            analysis_end=bounds.analysis_end,
            warmup_start=bounds.warmup_start,
            required_warmup_candles=bounds.required_warmup_candles,
            warmup_candle_count=bounds.required_warmup_candles,
            analysis_candle_count=bounds.expected_analysis_candles,
            total_candle_count=bounds.expected_total_candles,
            first_open_time=candles[0].open_time,
            last_close_time=candles[-1].close_time,
            manifest_fingerprint=manifest_fingerprint,
            prepared_at=utc_now(),
        )
        snapshots = tuple(
            dataset_candle_from_manifest(
                dataset_id=dataset.id,
                position=position,
                candle=manifest_candle,
            )
            for position, manifest_candle in enumerate(manifest_candles)
        )
        await create_historical_analysis_dataset_candles(
            session,
            snapshots=snapshots,
        )
        await session.commit()
        _log_dataset_prepared(run, dataset)
        return HistoricalAnalysisDatasetPreparationResult(
            dataset=dataset,
            failure_code=None,
            replayed=False,
        )
    except IntegrityError:
        await session.rollback()
        logger.info(
            "historical.dataset.rejected run_id=%s failure_category=historical_dataset_correction_race",
            run_id,
        )
        return HistoricalAnalysisDatasetPreparationResult(
            dataset=None,
            failure_code="historical_dataset_correction_race",
            replayed=False,
        )
    except SQLAlchemyError:
        await session.rollback()
        logger.info(
            "historical.dataset.rejected run_id=%s failure_category=historical_dataset_unavailable",
            run_id,
        )
        return HistoricalAnalysisDatasetPreparationResult(
            dataset=None,
            failure_code="historical_dataset_unavailable",
            replayed=False,
        )


async def validate_historical_analysis_dataset_current(
    session: AsyncSession,
    dataset_id: uuid.UUID,
) -> HistoricalAnalysisDatasetValidationResult:
    """Mark a ready dataset stale when its canonical source no longer matches."""

    try:
        dataset = await get_historical_analysis_dataset(
            session,
            dataset_id=dataset_id,
            for_update=True,
        )
        if dataset is None:
            await session.rollback()
            return HistoricalAnalysisDatasetValidationResult(
                dataset=None,
                stale=False,
                failure_code="historical_dataset_unavailable",
            )
        if dataset.status != "ready":
            await session.commit()
            return HistoricalAnalysisDatasetValidationResult(
                dataset=dataset,
                stale=dataset.status == "stale",
                failure_code=dataset.failure_code,
            )

        run = await get_historical_analysis_run_by_id(
            session,
            run_id=dataset.run_id,
        )
        snapshots = await list_historical_analysis_dataset_candles(
            session,
            dataset_id=dataset.id,
        )
        stale = (
            run is None
            or not _run_matches_dataset(run, dataset)
            or not _snapshot_sequence_is_valid(dataset, snapshots)
        )
        current_by_id: dict[uuid.UUID, MarketCandle] = {}
        if not stale:
            current_candles = await get_market_candles_for_historical_dataset_share(
                session,
                candle_ids=[snapshot.candle_id for snapshot in snapshots],
            )
            current_by_id = {candle.id: candle for candle in current_candles}
            stale = len(current_by_id) != len(snapshots)

        if not stale:
            stale = any(
                not _snapshot_matches_current(
                    dataset,
                    snapshot,
                    current_by_id[snapshot.candle_id],
                )
                for snapshot in snapshots
            )

        if not stale and run is not None:
            try:
                bounds = bounds_from_dataset(dataset)
                fingerprint = calculate_historical_dataset_fingerprint(
                    run=run,
                    bounds=bounds,
                    candles=tuple(
                        manifest_candle_from_snapshot(snapshot)
                        for snapshot in snapshots
                    ),
                )
                stale = fingerprint != dataset.manifest_fingerprint
            except ValueError:
                stale = True

        if stale:
            now = utc_now()
            dataset.status = "stale"
            dataset.failure_code = "historical_dataset_stale"
            dataset.stale_at = now
            dataset.updated_at = now
            await session.commit()
            logger.info(
                "historical.dataset.stale run_id=%s dataset_id=%s market_id=%s "
                "preset_id=%s timeframe=%s warmup_count=%s analysis_count=%s "
                "total_count=%s failure_category=historical_dataset_stale",
                dataset.run_id,
                dataset.id,
                dataset.supported_market_id,
                dataset.signal_preset_id,
                dataset.timeframe,
                dataset.warmup_candle_count,
                dataset.analysis_candle_count,
                dataset.total_candle_count,
            )
            return HistoricalAnalysisDatasetValidationResult(
                dataset=dataset,
                stale=True,
                failure_code="historical_dataset_stale",
            )

        await session.commit()
        return HistoricalAnalysisDatasetValidationResult(
            dataset=dataset,
            stale=False,
            failure_code=None,
        )
    except SQLAlchemyError:
        await session.rollback()
        return HistoricalAnalysisDatasetValidationResult(
            dataset=None,
            stale=False,
            failure_code="historical_dataset_unavailable",
        )


def resolve_historical_dataset_bounds(
    run: HistoricalAnalysisRun,
) -> HistoricalDatasetBounds:
    timeframe = run.timeframe_snapshot
    timeframe_delta = TIMEFRAME_DELTAS.get(timeframe)
    timeframe_hours = TIMEFRAME_HOURS.get(timeframe)
    required_warmup_candles = REQUIRED_WARMUP_CANDLES.get(run.strategy_type_snapshot)
    expected_calculation_version = SUPPORTED_CALCULATION_VERSIONS.get(
        run.strategy_type_snapshot,
    )
    if (
        timeframe_delta is None
        or timeframe_hours is None
        or required_warmup_candles is None
        or expected_calculation_version != run.calculation_version_snapshot
    ):
        raise ValueError("The pinned historical-analysis request is unsupported.")

    analysis_start = normalize_utc_datetime(run.analysis_start)
    analysis_end = normalize_utc_datetime(run.analysis_end)
    if (
        analysis_end <= analysis_start
        or not is_timeframe_boundary(analysis_start, timeframe_hours)
        or not is_timeframe_boundary(analysis_end, timeframe_hours)
    ):
        raise ValueError("The historical-analysis range is invalid.")

    range_seconds = (analysis_end - analysis_start).total_seconds()
    timeframe_seconds = timeframe_delta.total_seconds()
    if range_seconds % timeframe_seconds != 0:
        raise ValueError("The historical-analysis range is not aligned.")
    expected_analysis_candles = int(range_seconds // timeframe_seconds)
    warmup_start = analysis_start - required_warmup_candles * timeframe_delta
    return HistoricalDatasetBounds(
        timeframe=timeframe,
        timeframe_delta=timeframe_delta,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        warmup_start=warmup_start,
        required_warmup_candles=required_warmup_candles,
        expected_analysis_candles=expected_analysis_candles,
        expected_total_candles=required_warmup_candles + expected_analysis_candles,
    )


def bounds_from_dataset(
    dataset: HistoricalAnalysisDataset,
) -> HistoricalDatasetBounds:
    timeframe_delta = TIMEFRAME_DELTAS.get(dataset.timeframe)
    timeframe_hours = TIMEFRAME_HOURS.get(dataset.timeframe)
    if timeframe_delta is None or timeframe_hours is None:
        raise ValueError("The dataset timeframe is unsupported.")
    analysis_start = normalize_utc_datetime(dataset.analysis_start)
    analysis_end = normalize_utc_datetime(dataset.analysis_end)
    warmup_start = normalize_utc_datetime(dataset.warmup_start)
    range_seconds = (analysis_end - analysis_start).total_seconds()
    timeframe_seconds = timeframe_delta.total_seconds()
    if (
        analysis_end <= analysis_start
        or warmup_start >= analysis_start
        or range_seconds % timeframe_seconds != 0
        or not is_timeframe_boundary(analysis_start, timeframe_hours)
        or not is_timeframe_boundary(analysis_end, timeframe_hours)
        or dataset.total_candle_count
        != dataset.required_warmup_candles
        + int(range_seconds // timeframe_seconds)
    ):
        raise ValueError("The dataset range is not aligned.")
    expected_analysis_candles = int(range_seconds // timeframe_seconds)
    return HistoricalDatasetBounds(
        timeframe=dataset.timeframe,
        timeframe_delta=timeframe_delta,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        warmup_start=warmup_start,
        required_warmup_candles=dataset.required_warmup_candles,
        expected_analysis_candles=expected_analysis_candles,
        expected_total_candles=dataset.total_candle_count,
    )


def validate_historical_dataset_coverage(
    run: HistoricalAnalysisRun,
    bounds: HistoricalDatasetBounds,
    candles: Sequence[MarketCandle],
) -> HistoricalDatasetFailureCode | None:
    if len(candles) > MAX_HISTORICAL_DATASET_CANDLES:
        return "historical_dataset_too_large"
    if not candles:
        return "historical_dataset_insufficient_warmup"

    seen_ids: set[uuid.UUID] = set()
    seen_open_times: set[datetime] = set()
    previous: MarketCandle | None = None
    warmup_count = 0
    analysis_count = 0
    for candle in candles:
        failure_code = validate_historical_dataset_candle(
            candle,
            bounds=bounds,
            supported_market_id=run.supported_market_id,
        )
        if failure_code is not None:
            return failure_code
        if candle.id in seen_ids or candle.open_time in seen_open_times:
            return "historical_dataset_invalid"
        if previous is not None:
            if candle.open_time <= previous.open_time:
                return "historical_dataset_invalid"
            if candle.open_time != previous.close_time:
                return "historical_dataset_gap_detected"
        seen_ids.add(candle.id)
        seen_open_times.add(candle.open_time)
        previous = candle
        if candle.open_time < bounds.analysis_start:
            warmup_count += 1
        else:
            analysis_count += 1

    first_candle = candles[0]
    last_candle = candles[-1]
    if first_candle.open_time != bounds.warmup_start:
        if first_candle.open_time > bounds.warmup_start:
            return "historical_dataset_insufficient_warmup"
        return "historical_dataset_invalid"
    if last_candle.close_time != bounds.analysis_end:
        return "historical_dataset_gap_detected"
    if warmup_count < bounds.required_warmup_candles:
        return "historical_dataset_insufficient_warmup"
    if warmup_count > bounds.required_warmup_candles:
        return "historical_dataset_invalid"
    if analysis_count < bounds.expected_analysis_candles:
        return "historical_dataset_gap_detected"
    if analysis_count > bounds.expected_analysis_candles:
        return "historical_dataset_invalid"
    if len(candles) != bounds.expected_total_candles:
        return "historical_dataset_invalid"
    return None


def validate_historical_dataset_candle(
    candle: MarketCandle,
    *,
    bounds: HistoricalDatasetBounds,
    supported_market_id: uuid.UUID,
) -> HistoricalDatasetFailureCode | None:
    if candle.status == "incomplete":
        return "historical_dataset_incomplete"
    if candle.status != "complete" or not candle.is_current:
        return "historical_dataset_invalid"
    if (
        candle.supported_market_id != supported_market_id
        or candle.timeframe != bounds.timeframe
    ):
        return "historical_dataset_invalid"
    if not _is_utc(candle.open_time) or not _is_utc(candle.close_time):
        return "historical_dataset_invalid"
    if candle.close_time != candle.open_time + bounds.timeframe_delta:
        return "historical_dataset_invalid"
    if not _is_valid_decimal(candle.open_price, positive=True):
        return "historical_dataset_invalid"
    if not _is_valid_decimal(candle.high_price, positive=True):
        return "historical_dataset_invalid"
    if not _is_valid_decimal(candle.low_price, positive=True):
        return "historical_dataset_invalid"
    if not _is_valid_decimal(candle.close_price, positive=True):
        return "historical_dataset_invalid"
    if not _is_valid_decimal(candle.base_volume, positive=False):
        return "historical_dataset_invalid"
    if not _is_valid_decimal(candle.quote_volume, positive=False):
        return "historical_dataset_invalid"
    if candle.trade_count is None or candle.trade_count < 0:
        return "historical_dataset_invalid"
    expected_source_count = EXPECTED_SOURCE_CANDLE_COUNTS.get(bounds.timeframe)
    if (
        candle.source_kind != "aggregate_1m"
        or expected_source_count is None
        or candle.expected_source_candle_count != expected_source_count
        or candle.source_candle_count != expected_source_count
    ):
        return "historical_dataset_invalid"
    if (
        candle.high_price < candle.open_price
        or candle.high_price < candle.close_price
        or candle.high_price < candle.low_price
        or candle.low_price > candle.open_price
        or candle.low_price > candle.close_price
    ):
        return "historical_dataset_invalid"
    if candle.source_fingerprint is not None and (
        len(candle.source_fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in candle.source_fingerprint)
    ):
        return "historical_dataset_invalid"
    if candle.open_time.minute != 0 or candle.open_time.second != 0:
        return "historical_dataset_invalid"
    if bounds.timeframe == "4h" and candle.open_time.hour % 4 != 0:
        return "historical_dataset_invalid"
    return None


def calculate_historical_dataset_fingerprint(
    *,
    run: HistoricalAnalysisRun,
    bounds: HistoricalDatasetBounds,
    candles: Sequence[ManifestCandle],
) -> str:
    payload: list[object] = [
        FINGERPRINT_SCHEMA_VERSION,
        str(run.supported_market_id),
        str(run.signal_preset_id),
        run.preset_code_snapshot,
        run.preset_version_snapshot,
        run.calculation_version_snapshot,
        bounds.timeframe,
        _utc_z(bounds.analysis_start),
        _utc_z(bounds.analysis_end),
        bounds.required_warmup_candles,
    ]
    payload.extend(
        [
            [
                str(candle.candle_id),
                candle.candle_revision,
                _utc_z(candle.open_time),
                _utc_z(candle.close_time),
                _decimal_string(candle.open_price),
                _decimal_string(candle.high_price),
                _decimal_string(candle.low_price),
                _decimal_string(candle.close_price),
                _decimal_string(candle.base_volume),
                _decimal_string(candle.quote_volume),
                candle.trade_count,
                candle.source_kind,
                candle.source_candle_count,
                candle.expected_source_candle_count,
                candle.source_fingerprint or "",
            ]
            for candle in candles
        ]
    )
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def normalize_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("The value must be an aware UTC timestamp.")
    return value.astimezone(UTC)


def is_timeframe_boundary(value: datetime, timeframe_hours: int) -> bool:
    return (
        value.minute == 0
        and value.second == 0
        and value.microsecond == 0
        and value.hour % timeframe_hours == 0
    )


def manifest_candle_from_market(
    candle: MarketCandle,
    *,
    bounds: HistoricalDatasetBounds,
) -> ManifestCandle:
    return ManifestCandle(
        candle_id=candle.id,
        candle_revision=candle.revision,
        is_warmup=candle.open_time < bounds.analysis_start,
        timeframe=candle.timeframe,
        open_time=candle.open_time,
        close_time=candle.close_time,
        open_price=_required_decimal(candle.open_price),
        high_price=_required_decimal(candle.high_price),
        low_price=_required_decimal(candle.low_price),
        close_price=_required_decimal(candle.close_price),
        base_volume=_required_decimal(candle.base_volume),
        quote_volume=_required_decimal(candle.quote_volume),
        trade_count=_required_integer(candle.trade_count),
        source_kind=candle.source_kind,
        source_candle_count=candle.source_candle_count,
        expected_source_candle_count=candle.expected_source_candle_count,
        source_fingerprint=candle.source_fingerprint,
    )


def manifest_candle_from_snapshot(
    snapshot: HistoricalAnalysisDatasetCandle,
) -> ManifestCandle:
    return ManifestCandle(
        candle_id=snapshot.candle_id,
        candle_revision=snapshot.candle_revision,
        is_warmup=snapshot.is_warmup,
        timeframe=snapshot.timeframe,
        open_time=snapshot.open_time,
        close_time=snapshot.close_time,
        open_price=snapshot.open_price,
        high_price=snapshot.high_price,
        low_price=snapshot.low_price,
        close_price=snapshot.close_price,
        base_volume=snapshot.base_volume,
        quote_volume=snapshot.quote_volume,
        trade_count=snapshot.trade_count,
        source_kind=snapshot.source_kind,
        source_candle_count=snapshot.source_candle_count,
        expected_source_candle_count=snapshot.expected_source_candle_count,
        source_fingerprint=snapshot.source_fingerprint,
    )


def dataset_candle_from_manifest(
    *,
    dataset_id: uuid.UUID,
    position: int,
    candle: ManifestCandle,
) -> HistoricalAnalysisDatasetCandle:
    return HistoricalAnalysisDatasetCandle(
        dataset_id=dataset_id,
        position=position,
        candle_id=candle.candle_id,
        candle_revision=candle.candle_revision,
        is_warmup=candle.is_warmup,
        timeframe=candle.timeframe,
        open_time=candle.open_time,
        close_time=candle.close_time,
        open_price=candle.open_price,
        high_price=candle.high_price,
        low_price=candle.low_price,
        close_price=candle.close_price,
        base_volume=candle.base_volume,
        quote_volume=candle.quote_volume,
        trade_count=candle.trade_count,
        source_kind=candle.source_kind,
        source_candle_count=candle.source_candle_count,
        expected_source_candle_count=candle.expected_source_candle_count,
        source_fingerprint=candle.source_fingerprint,
    )


async def _create_failed_dataset(
    session: AsyncSession,
    *,
    run: HistoricalAnalysisRun,
    bounds: HistoricalDatasetBounds,
    failure_code: HistoricalDatasetFailureCode,
    candles: Sequence[MarketCandle],
) -> HistoricalAnalysisDataset:
    if len(candles) > MAX_HISTORICAL_DATASET_CANDLES:
        warmup_count = 0
        analysis_count = 0
    else:
        warmup_count = sum(
            candle.open_time < bounds.analysis_start
            for candle in candles
        )
        analysis_count = len(candles) - warmup_count
    fingerprint = calculate_historical_dataset_fingerprint(
        run=run,
        bounds=bounds,
        candles=(),
    )
    return await create_historical_analysis_dataset(
        session,
        run_id=run.id,
        supported_market_id=run.supported_market_id,
        signal_preset_id=run.signal_preset_id,
        status="failed",
        failure_code=failure_code,
        timeframe=bounds.timeframe,
        analysis_start=bounds.analysis_start,
        analysis_end=bounds.analysis_end,
        warmup_start=bounds.warmup_start,
        required_warmup_candles=bounds.required_warmup_candles,
        warmup_candle_count=warmup_count,
        analysis_candle_count=analysis_count,
        total_candle_count=warmup_count + analysis_count,
        first_open_time=bounds.warmup_start,
        last_close_time=bounds.analysis_end,
        manifest_fingerprint=fingerprint,
        prepared_at=utc_now(),
    )


def _snapshot_sequence_is_valid(
    dataset: HistoricalAnalysisDataset,
    snapshots: Sequence[HistoricalAnalysisDatasetCandle],
) -> bool:
    if dataset.total_candle_count <= 0 or len(snapshots) != dataset.total_candle_count:
        return False
    for position, snapshot in enumerate(snapshots):
        if snapshot.dataset_id != dataset.id or snapshot.position != position:
            return False
    return True


def _run_matches_dataset(
    run: HistoricalAnalysisRun,
    dataset: HistoricalAnalysisDataset,
) -> bool:
    return (
        run.supported_market_id == dataset.supported_market_id
        and run.signal_preset_id == dataset.signal_preset_id
        and run.timeframe_snapshot == dataset.timeframe
        and run.analysis_start == dataset.analysis_start
        and run.analysis_end == dataset.analysis_end
    )


def _snapshot_matches_current(
    dataset: HistoricalAnalysisDataset,
    snapshot: HistoricalAnalysisDatasetCandle,
    current: MarketCandle,
) -> bool:
    return (
        current.id == snapshot.candle_id
        and current.is_current
        and current.status == "complete"
        and current.supported_market_id == dataset.supported_market_id
        and current.timeframe == snapshot.timeframe == dataset.timeframe
        and current.open_time == snapshot.open_time
        and current.close_time == snapshot.close_time
        and current.revision == snapshot.candle_revision
        and current.open_price == snapshot.open_price
        and current.high_price == snapshot.high_price
        and current.low_price == snapshot.low_price
        and current.close_price == snapshot.close_price
        and current.base_volume == snapshot.base_volume
        and current.quote_volume == snapshot.quote_volume
        and current.trade_count == snapshot.trade_count
        and current.source_kind == snapshot.source_kind
        and current.source_candle_count == snapshot.source_candle_count
        and current.expected_source_candle_count == snapshot.expected_source_candle_count
        and current.source_fingerprint == snapshot.source_fingerprint
    )


def _is_valid_decimal(value: Decimal | None, *, positive: bool) -> bool:
    if value is None or not isinstance(value, Decimal) or not value.is_finite():
        return False
    return value > 0 if positive else value >= 0


def _required_decimal(value: Decimal | None) -> Decimal:
    if value is None or not isinstance(value, Decimal):
        raise ValueError("The selected candle is not fully valued.")
    return value


def _required_integer(value: int | None) -> int:
    if value is None:
        raise ValueError("The selected candle is not fully valued.")
    return value


def _is_utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() == timedelta(0)


def _utc_z(value: datetime) -> str:
    return normalize_utc_datetime(value).isoformat(
        timespec="microseconds",
    ).replace("+00:00", "Z")


def _decimal_string(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("Fingerprint values must be finite.")
    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return "0" if normalized in {"", "-0"} else normalized


def _log_dataset_prepared(
    run: HistoricalAnalysisRun,
    dataset: HistoricalAnalysisDataset,
) -> None:
    logger.info(
        "historical.dataset.prepared run_id=%s dataset_id=%s market_id=%s "
        "preset_id=%s timeframe=%s warmup_count=%s analysis_count=%s total_count=%s",
        run.id,
        dataset.id,
        dataset.supported_market_id,
        dataset.signal_preset_id,
        dataset.timeframe,
        dataset.warmup_candle_count,
        dataset.analysis_candle_count,
        dataset.total_candle_count,
    )


def _log_dataset_replayed(
    run: HistoricalAnalysisRun,
    dataset: HistoricalAnalysisDataset,
) -> None:
    logger.info(
        "historical.dataset.replayed run_id=%s dataset_id=%s market_id=%s "
        "preset_id=%s timeframe=%s warmup_count=%s analysis_count=%s total_count=%s",
        run.id,
        dataset.id,
        dataset.supported_market_id,
        dataset.signal_preset_id,
        dataset.timeframe,
        dataset.warmup_candle_count,
        dataset.analysis_candle_count,
        dataset.total_candle_count,
    )


def _log_dataset_rejected(
    run: HistoricalAnalysisRun,
    dataset: HistoricalAnalysisDataset,
    failure_code: HistoricalDatasetFailureCode,
) -> None:
    logger.info(
        "historical.dataset.rejected run_id=%s dataset_id=%s market_id=%s "
        "preset_id=%s timeframe=%s warmup_count=%s analysis_count=%s "
        "total_count=%s failure_category=%s",
        run.id,
        dataset.id,
        dataset.supported_market_id,
        dataset.signal_preset_id,
        dataset.timeframe,
        dataset.warmup_candle_count,
        dataset.analysis_candle_count,
        dataset.total_candle_count,
        failure_code,
    )
