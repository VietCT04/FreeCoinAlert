"""Pure deterministic simulation for the fixed historical-analysis presets."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Literal
from uuid import UUID

from freecoinalert_api.signals.crossings import crosses
from freecoinalert_api.strategies import (
    StrategyCandle,
    calculate_rsi_series,
    calculate_sma_series,
)
from freecoinalert_api.strategies.decimal_math import CALCULATION_PRECISION
from freecoinalert_api.strategies.errors import StrategyCalculationError


ENGINE_VERSION = "historical_fixed_preset_v1"
ASSUMPTION_VERSION = "fixed_horizon_v1"
RESULT_FINGERPRINT_SCHEMA_VERSION = "historical_simulation_result_v1"

MAX_TOTAL_CANDLES = 2_500
MAX_ANALYSIS_CANDLES = 2_200
HOLDING_PERIOD_CANDLES = 6
DISPLAY_QUANTUM = Decimal("0.00000001")
INITIAL_EQUITY = Decimal("10000")
SLIPPAGE_RATE = Decimal("0.0005")
FEE_RATE = Decimal("0.001")

Timeframe = Literal["1h", "4h"]
SignalDirection = Literal["cross_above", "cross_below"]
PositionDirection = Literal["long", "synthetic_short"]
PositionState = Literal["flat", "long", "synthetic_short"]
TradeOutcome = Literal["win", "loss", "flat"]

SimulationStatus = Literal[
    "success",
    "insufficient_history",
    "invalid_input",
    "gap_detected",
    "unsupported_preset",
    "unsupported_calculation_version",
    "unsupported_engine_version",
    "unsupported_assumption_version",
]

FailureReason = Literal[
    "input_type_invalid",
    "dataset_not_ready",
    "dataset_identity_mismatch",
    "dataset_fingerprint_invalid",
    "dataset_range_invalid",
    "dataset_count_invalid",
    "resource_limit_exceeded",
    "preset_identity_mismatch",
    "preset_configuration_invalid",
    "calculation_invariant",
    "candle_identity_invalid",
    "candle_value_invalid",
    "candle_sequence_invalid",
    "candle_gap",
    "missing_warmup",
    "missing_analysis_candles",
]

UndefinedMetricReason = Literal["no_trades", "no_losing_trades"]

SAFETY_DISCLOSURES: tuple[str, ...] = (
    "historical hypothetical simulation",
    "not financial advice",
    "not a prediction",
    "not a delivery or profit guarantee",
    "synthetic short results are not executable Binance Spot trades",
)

_TIMEFRAME_DELTAS: dict[Timeframe, timedelta] = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}
_TIMEFRAME_HOURS: dict[Timeframe, int] = {"1h": 1, "4h": 4}
_EXPECTED_SOURCE_CANDLE_COUNTS: dict[Timeframe, int] = {
    "1h": 60,
    "4h": 240,
}
_CALCULATION_VERSIONS = {
    "price_sma_cross": "sma_close_v1",
    "rsi_threshold_cross": "rsi_wilder_close_v1",
}
_WARMUP_CANDLE_COUNTS = {
    "price_sma_cross": 200,
    "rsi_threshold_cross": 15,
}
_PRESET_SPECS: dict[str, tuple[str, Timeframe, SignalDirection, int, Decimal | None]] = {
    "price_sma_200_cross_above_1h": (
        "price_sma_cross",
        "1h",
        "cross_above",
        200,
        None,
    ),
    "price_sma_200_cross_below_1h": (
        "price_sma_cross",
        "1h",
        "cross_below",
        200,
        None,
    ),
    "rsi_14_cross_above_70_1h": (
        "rsi_threshold_cross",
        "1h",
        "cross_above",
        14,
        Decimal("70"),
    ),
    "rsi_14_cross_below_30_1h": (
        "rsi_threshold_cross",
        "1h",
        "cross_below",
        14,
        Decimal("30"),
    ),
    "price_sma_200_cross_above_4h": (
        "price_sma_cross",
        "4h",
        "cross_above",
        200,
        None,
    ),
    "price_sma_200_cross_below_4h": (
        "price_sma_cross",
        "4h",
        "cross_below",
        200,
        None,
    ),
    "rsi_14_cross_above_70_4h": (
        "rsi_threshold_cross",
        "4h",
        "cross_above",
        14,
        Decimal("70"),
    ),
    "rsi_14_cross_below_30_4h": (
        "rsi_threshold_cross",
        "4h",
        "cross_below",
        14,
        Decimal("30"),
    ),
}


@dataclass(frozen=True, slots=True)
class HistoricalDatasetManifest:
    """Immutable dataset metadata supplied by the dataset preparation boundary."""

    dataset_id: UUID
    supported_market_id: UUID
    signal_preset_id: UUID
    status: Literal["ready", "stale", "failed"]
    timeframe: Timeframe
    analysis_start: datetime
    analysis_end: datetime
    warmup_start: datetime
    required_warmup_candles: int
    warmup_candle_count: int
    analysis_candle_count: int
    total_candle_count: int
    first_open_time: datetime
    last_close_time: datetime
    manifest_fingerprint: str


@dataclass(frozen=True, slots=True)
class HistoricalSimulationCandle:
    """A complete immutable candle snapshot consumed by the pure engine."""

    dataset_id: UUID
    position: int
    candle_id: UUID
    candle_revision: int
    is_warmup: bool
    timeframe: Timeframe
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
    status: Literal["complete"] = "complete"


@dataclass(frozen=True, slots=True)
class HistoricalPresetSnapshot:
    """Pinned server-controlled preset meaning supplied to the engine."""

    preset_id: UUID
    code: str
    version: int
    strategy_type: str
    timeframe: Timeframe
    direction: SignalDirection
    period: int
    threshold: Decimal | None
    price_input: Literal["close"]


@dataclass(frozen=True, slots=True)
class FixedHorizonAssumptions:
    """The complete server-controlled ``fixed_horizon_v1`` contract."""

    initial_equity: Decimal
    signal_timing: Literal["confirmed_candle_close"]
    entry_timing: Literal["next_candle_open"]
    holding_period_candles: int
    position_direction: Literal["cross_above_long_cross_below_synthetic_short"]
    position_sizing: Literal["one_position_full_equity"]
    concurrent_positions: int
    overlapping_signals: Literal["ignored"]
    entry_slippage_rate: Decimal
    exit_slippage_rate: Decimal
    fee_rate: Decimal
    stop_loss: None
    take_profit: None
    early_exit: None
    end_of_range: Literal["incomplete_trade_not_opened"]
    compounding: Literal["prior_net_closing_equity"]
    short_loss_cap: Literal["allocated_equity"]


FIXED_HORIZON_V1_ASSUMPTIONS = FixedHorizonAssumptions(
    initial_equity=INITIAL_EQUITY,
    signal_timing="confirmed_candle_close",
    entry_timing="next_candle_open",
    holding_period_candles=HOLDING_PERIOD_CANDLES,
    position_direction="cross_above_long_cross_below_synthetic_short",
    position_sizing="one_position_full_equity",
    concurrent_positions=1,
    overlapping_signals="ignored",
    entry_slippage_rate=SLIPPAGE_RATE,
    exit_slippage_rate=SLIPPAGE_RATE,
    fee_rate=FEE_RATE,
    stop_loss=None,
    take_profit=None,
    early_exit=None,
    end_of_range="incomplete_trade_not_opened",
    compounding="prior_net_closing_equity",
    short_loss_cap="allocated_equity",
)


@dataclass(frozen=True, slots=True)
class HistoricalSimulationInput:
    """Pure immutable input for one market, preset, and dataset simulation."""

    dataset: HistoricalDatasetManifest
    preset: HistoricalPresetSnapshot
    calculation_version: str
    analysis_start: datetime
    analysis_end: datetime
    candles: tuple[HistoricalSimulationCandle, ...]
    engine_version: str = ENGINE_VERSION
    assumption_version: str = ASSUMPTION_VERSION
    assumptions: FixedHorizonAssumptions = FIXED_HORIZON_V1_ASSUMPTIONS


@dataclass(frozen=True, slots=True)
class HistoricalSimulationTrade:
    sequence: int
    signal_candle_id: UUID
    signal_candle_revision: int
    signal_open_time: datetime
    signal_close_time: datetime
    signal_direction: SignalDirection
    position_direction: PositionDirection
    entry_candle_id: UUID
    entry_candle_revision: int
    entry_open_time: datetime
    entry_raw_price: Decimal
    entry_fill_price: Decimal
    exit_candle_id: UUID
    exit_candle_revision: int
    exit_close_time: datetime
    exit_raw_price: Decimal
    exit_fill_price: Decimal
    holding_candle_count: int
    fee_rate: Decimal
    slippage_rate: Decimal
    equity_before: Decimal
    gross_return: Decimal
    net_return: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    equity_after: Decimal
    outcome: TradeOutcome


@dataclass(frozen=True, slots=True)
class HistoricalSimulationEquityPoint:
    sequence: int
    candle_id: UUID
    candle_revision: int
    candle_open_time: datetime
    candle_close_time: datetime
    equity: Decimal
    drawdown: Decimal
    position_state: PositionState
    active_trade_sequence: int | None


@dataclass(frozen=True, slots=True)
class HistoricalSimulationSummary:
    analysis_candle_count: int
    signal_count: int
    executed_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    flat_trade_count: int
    overlapping_signal_count: int
    insufficient_forward_window_signal_count: int
    equity_exhausted_signal_count: int
    initial_equity: Decimal
    final_equity: Decimal
    gross_return: Decimal
    net_return: Decimal
    maximum_drawdown: Decimal
    win_rate: Decimal | None
    win_rate_undefined_reason: UndefinedMetricReason | None
    profit_factor: Decimal | None
    profit_factor_undefined_reason: UndefinedMetricReason | None


@dataclass(frozen=True, slots=True)
class HistoricalSimulationResult:
    status: SimulationStatus
    failure_reason: FailureReason | None
    dataset_fingerprint: str | None
    preset_code: str | None
    preset_version: int | None
    calculation_version: str | None
    engine_version: str | None
    assumption_version: str | None
    analysis_start: datetime | None
    analysis_end: datetime | None
    assumptions: FixedHorizonAssumptions | None
    trades: tuple[HistoricalSimulationTrade, ...]
    equity_series: tuple[HistoricalSimulationEquityPoint, ...]
    summary: HistoricalSimulationSummary | None
    safety_disclosures: tuple[str, ...]
    result_fingerprint: str | None

    def to_serializable(self) -> dict[str, object]:
        """Return a JSON-compatible result with eight-place Decimal strings."""

        return {
            "status": self.status,
            "failure_reason": self.failure_reason,
            "dataset_fingerprint": self.dataset_fingerprint,
            "preset_code": self.preset_code,
            "preset_version": self.preset_version,
            "calculation_version": self.calculation_version,
            "engine_version": self.engine_version,
            "assumption_version": self.assumption_version,
            "analysis_start": _optional_utc_z(self.analysis_start),
            "analysis_end": _optional_utc_z(self.analysis_end),
            "assumptions": _assumptions_payload(self.assumptions),
            "trades": [_trade_payload(trade) for trade in self.trades],
            "equity_series": [
                _equity_point_payload(point) for point in self.equity_series
            ],
            "summary": _summary_payload(self.summary),
            "safety_disclosures": list(self.safety_disclosures),
            "result_fingerprint": self.result_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class _ValidatedSimulationInput:
    dataset: HistoricalDatasetManifest
    preset: HistoricalPresetSnapshot
    calculation_version: str
    analysis_start: datetime
    analysis_end: datetime
    candles: tuple[HistoricalSimulationCandle, ...]
    assumptions: FixedHorizonAssumptions


@dataclass(frozen=True, slots=True)
class _SignalObservation:
    analysis_sequence: int
    candle_index: int
    candle: HistoricalSimulationCandle
    signal_direction: SignalDirection
    previous_left_value: Decimal
    previous_right_value: Decimal
    current_left_value: Decimal
    current_right_value: Decimal
    triggered: bool


@dataclass(frozen=True, slots=True)
class _PendingTrade:
    sequence: int
    signal: _SignalObservation
    entry_index: int
    exit_index: int
    equity_before: Decimal


@dataclass(frozen=True, slots=True)
class _OpenTrade:
    pending: _PendingTrade
    entry_candle: HistoricalSimulationCandle
    entry_fill_price: Decimal


class _ValidationFailure(Exception):
    def __init__(self, status: SimulationStatus, reason: FailureReason) -> None:
        self.status = status
        self.reason = reason
        super().__init__(reason)


def simulate_fixed_preset(
    input: HistoricalSimulationInput,
) -> HistoricalSimulationResult:
    """Simulate one fixed preset over one immutable canonical candle dataset."""

    try:
        validated = _validate_input(input)
        observations = _calculate_observations(validated)
        result = _simulate(validated, observations)
        return replace(result, result_fingerprint=_result_fingerprint(result))
    except _ValidationFailure as failure:
        return _failure_result(input, failure.status, failure.reason)
    except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError):
        return _failure_result(input, "invalid_input", "calculation_invariant")
    except StrategyCalculationError:
        return _failure_result(input, "invalid_input", "calculation_invariant")


def _validate_input(input: HistoricalSimulationInput) -> _ValidatedSimulationInput:
    if not isinstance(input, HistoricalSimulationInput):
        raise _ValidationFailure("invalid_input", "input_type_invalid")
    if input.engine_version != ENGINE_VERSION:
        raise _ValidationFailure(
            "unsupported_engine_version",
            "calculation_invariant",
        )
    if input.assumption_version != ASSUMPTION_VERSION:
        raise _ValidationFailure(
            "unsupported_assumption_version",
            "calculation_invariant",
        )
    if input.assumptions != FIXED_HORIZON_V1_ASSUMPTIONS:
        raise _ValidationFailure(
            "unsupported_assumption_version",
            "calculation_invariant",
        )

    preset = input.preset
    dataset = input.dataset
    if not isinstance(preset, HistoricalPresetSnapshot) or not isinstance(
        dataset,
        HistoricalDatasetManifest,
    ):
        raise _ValidationFailure("invalid_input", "input_type_invalid")
    _validate_preset(preset, input.calculation_version)
    if not isinstance(preset.preset_id, UUID) or not isinstance(dataset.dataset_id, UUID):
        raise _ValidationFailure("invalid_input", "preset_identity_mismatch")
    if dataset.signal_preset_id != preset.preset_id:
        raise _ValidationFailure("invalid_input", "preset_identity_mismatch")
    if not isinstance(dataset.supported_market_id, UUID):
        raise _ValidationFailure("invalid_input", "dataset_identity_mismatch")
    if dataset.status != "ready":
        raise _ValidationFailure("invalid_input", "dataset_not_ready")

    analysis_start = _normalize_utc_datetime(input.analysis_start)
    analysis_end = _normalize_utc_datetime(input.analysis_end)
    manifest = _normalized_manifest(dataset)
    if analysis_start != manifest.analysis_start or analysis_end != manifest.analysis_end:
        raise _ValidationFailure("invalid_input", "dataset_range_invalid")
    if manifest.timeframe != preset.timeframe:
        raise _ValidationFailure("invalid_input", "dataset_identity_mismatch")
    if not _is_fingerprint(manifest.manifest_fingerprint):
        raise _ValidationFailure("invalid_input", "dataset_fingerprint_invalid")

    required_warmup = _WARMUP_CANDLE_COUNTS[preset.strategy_type]
    timeframe_delta = _TIMEFRAME_DELTAS[preset.timeframe]
    if not _is_timeframe_boundary(analysis_start, preset.timeframe):
        raise _ValidationFailure("invalid_input", "dataset_range_invalid")
    if analysis_end <= analysis_start:
        raise _ValidationFailure("invalid_input", "dataset_range_invalid")
    range_seconds = (analysis_end - analysis_start).total_seconds()
    timeframe_seconds = timeframe_delta.total_seconds()
    if range_seconds % timeframe_seconds != 0:
        raise _ValidationFailure("invalid_input", "dataset_range_invalid")
    expected_analysis = int(range_seconds // timeframe_seconds)
    expected_total = required_warmup + expected_analysis
    if expected_analysis > MAX_ANALYSIS_CANDLES or expected_total > MAX_TOTAL_CANDLES:
        raise _ValidationFailure("invalid_input", "resource_limit_exceeded")
    expected_warmup_start = analysis_start - required_warmup * timeframe_delta
    if (
        manifest.warmup_start != expected_warmup_start
        or manifest.required_warmup_candles != required_warmup
        or manifest.warmup_candle_count != required_warmup
        or manifest.analysis_candle_count != expected_analysis
        or manifest.total_candle_count != expected_total
        or manifest.first_open_time != expected_warmup_start
        or manifest.last_close_time != analysis_end
    ):
        raise _ValidationFailure("invalid_input", "dataset_count_invalid")

    if not isinstance(input.candles, tuple):
        raise _ValidationFailure("invalid_input", "input_type_invalid")
    if len(input.candles) == 0:
        raise _ValidationFailure("insufficient_history", "missing_warmup")
    if len(input.candles) > expected_total:
        raise _ValidationFailure("invalid_input", "dataset_count_invalid")

    candles = _validate_candles(
        input.candles,
        dataset=manifest,
        required_warmup=required_warmup,
        expected_analysis=expected_analysis,
        timeframe_delta=timeframe_delta,
    )
    return _ValidatedSimulationInput(
        dataset=manifest,
        preset=preset,
        calculation_version=input.calculation_version,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        candles=candles,
        assumptions=input.assumptions,
    )


def _validate_preset(
    preset: HistoricalPresetSnapshot,
    calculation_version: str,
) -> None:
    spec = _PRESET_SPECS.get(preset.code)
    if spec is None or preset.version != 1:
        raise _ValidationFailure("unsupported_preset", "preset_configuration_invalid")
    strategy_type, timeframe, direction, period, threshold = spec
    if (
        preset.strategy_type != strategy_type
        or preset.timeframe != timeframe
        or preset.direction != direction
        or preset.period != period
        or preset.threshold != threshold
        or preset.price_input != "close"
    ):
        raise _ValidationFailure("unsupported_preset", "preset_configuration_invalid")
    expected_calculation_version = _CALCULATION_VERSIONS[strategy_type]
    if calculation_version != expected_calculation_version:
        raise _ValidationFailure(
            "unsupported_calculation_version",
            "calculation_invariant",
        )


def _normalized_manifest(
    dataset: HistoricalDatasetManifest,
) -> HistoricalDatasetManifest:
    try:
        return replace(
            dataset,
            analysis_start=_normalize_utc_datetime(dataset.analysis_start),
            analysis_end=_normalize_utc_datetime(dataset.analysis_end),
            warmup_start=_normalize_utc_datetime(dataset.warmup_start),
            first_open_time=_normalize_utc_datetime(dataset.first_open_time),
            last_close_time=_normalize_utc_datetime(dataset.last_close_time),
        )
    except (AttributeError, TypeError, ValueError):
        raise _ValidationFailure("invalid_input", "dataset_range_invalid") from None


def _validate_candles(
    input_candles: tuple[HistoricalSimulationCandle, ...],
    *,
    dataset: HistoricalDatasetManifest,
    required_warmup: int,
    expected_analysis: int,
    timeframe_delta: timedelta,
) -> tuple[HistoricalSimulationCandle, ...]:
    seen_ids: set[UUID] = set()
    seen_open_times: set[datetime] = set()
    normalized: list[HistoricalSimulationCandle] = []
    previous: HistoricalSimulationCandle | None = None
    warmup_count = 0
    analysis_count = 0

    for position, raw_candle in enumerate(input_candles):
        if not isinstance(raw_candle, HistoricalSimulationCandle):
            raise _ValidationFailure("invalid_input", "input_type_invalid")
        candle = _normalized_candle(raw_candle)
        if (
            candle.dataset_id != dataset.dataset_id
            or not isinstance(candle.position, int)
            or isinstance(candle.position, bool)
            or candle.position != position
            or not isinstance(candle.candle_revision, int)
            or isinstance(candle.candle_revision, bool)
            or candle.candle_revision < 1
            or candle.status != "complete"
            or not isinstance(candle.is_warmup, bool)
            or candle.timeframe != dataset.timeframe
            or not isinstance(candle.candle_id, UUID)
        ):
            raise _ValidationFailure("invalid_input", "candle_identity_invalid")
        if candle.candle_id in seen_ids or candle.open_time in seen_open_times:
            raise _ValidationFailure("invalid_input", "candle_sequence_invalid")
        if candle.open_time < dataset.warmup_start or candle.open_time >= dataset.analysis_end:
            raise _ValidationFailure("invalid_input", "candle_sequence_invalid")
        if candle.close_time != candle.open_time + timeframe_delta:
            raise _ValidationFailure("invalid_input", "candle_value_invalid")
        if not _is_timeframe_boundary(candle.open_time, candle.timeframe):
            raise _ValidationFailure("invalid_input", "candle_value_invalid")
        if not _valid_candle_values(
            candle,
            expected_source_count=_EXPECTED_SOURCE_CANDLE_COUNTS[dataset.timeframe],
        ):
            raise _ValidationFailure("invalid_input", "candle_value_invalid")
        if previous is not None:
            if candle.open_time <= previous.open_time:
                raise _ValidationFailure("invalid_input", "candle_sequence_invalid")
            if candle.open_time != previous.close_time:
                raise _ValidationFailure("gap_detected", "candle_gap")
        seen_ids.add(candle.candle_id)
        seen_open_times.add(candle.open_time)
        normalized.append(candle)
        previous = candle
        if candle.open_time < dataset.analysis_start:
            if not candle.is_warmup:
                raise _ValidationFailure("invalid_input", "candle_identity_invalid")
            warmup_count += 1
        else:
            if candle.is_warmup:
                raise _ValidationFailure("invalid_input", "candle_identity_invalid")
            analysis_count += 1

    first_candle = normalized[0]
    if first_candle.open_time > dataset.warmup_start or warmup_count < required_warmup:
        raise _ValidationFailure("insufficient_history", "missing_warmup")
    if first_candle.open_time < dataset.warmup_start:
        raise _ValidationFailure("invalid_input", "candle_sequence_invalid")
    if analysis_count > expected_analysis or warmup_count > required_warmup:
        raise _ValidationFailure("invalid_input", "dataset_count_invalid")
    if len(normalized) < dataset.total_candle_count:
        if previous is not None and previous.close_time < dataset.analysis_end:
            raise _ValidationFailure("gap_detected", "candle_gap")
        raise _ValidationFailure("insufficient_history", "missing_analysis_candles")
    if previous is None or previous.close_time != dataset.analysis_end:
        raise _ValidationFailure("gap_detected", "candle_gap")
    if warmup_count != required_warmup or analysis_count != expected_analysis:
        raise _ValidationFailure("invalid_input", "dataset_count_invalid")
    return tuple(normalized)


def _normalized_candle(
    candle: HistoricalSimulationCandle,
) -> HistoricalSimulationCandle:
    try:
        return replace(
            candle,
            open_time=_normalize_utc_datetime(candle.open_time),
            close_time=_normalize_utc_datetime(candle.close_time),
        )
    except (AttributeError, TypeError, ValueError):
        raise _ValidationFailure("invalid_input", "candle_value_invalid") from None


def _valid_candle_values(
    candle: HistoricalSimulationCandle,
    *,
    expected_source_count: int,
) -> bool:
    if not _is_decimal(candle.open_price, positive=True):
        return False
    if not _is_decimal(candle.high_price, positive=True):
        return False
    if not _is_decimal(candle.low_price, positive=True):
        return False
    if not _is_decimal(candle.close_price, positive=True):
        return False
    if not _is_decimal(candle.base_volume, positive=False):
        return False
    if not _is_decimal(candle.quote_volume, positive=False):
        return False
    if not isinstance(candle.trade_count, int) or isinstance(candle.trade_count, bool):
        return False
    if candle.trade_count < 0:
        return False
    if candle.high_price < max(candle.open_price, candle.close_price, candle.low_price):
        return False
    if candle.low_price > min(candle.open_price, candle.close_price):
        return False
    if candle.source_kind != "aggregate_1m":
        return False
    if (
        not isinstance(candle.source_candle_count, int)
        or isinstance(candle.source_candle_count, bool)
        or candle.source_candle_count != expected_source_count
    ):
        return False
    if (
        not isinstance(candle.expected_source_candle_count, int)
        or isinstance(candle.expected_source_candle_count, bool)
        or candle.expected_source_candle_count != expected_source_count
    ):
        return False
    return candle.source_fingerprint is None or _is_fingerprint(candle.source_fingerprint)


def _calculate_observations(
    input: _ValidatedSimulationInput,
) -> tuple[_SignalObservation, ...]:
    strategy_candles = tuple(
        StrategyCandle(
            candle_id=candle.candle_id,
            candle_revision=candle.candle_revision,
            supported_market_id=input.dataset.supported_market_id,
            timeframe=candle.timeframe,
            open_time=candle.open_time,
            close_time=candle.close_time,
            close_price=candle.close_price,
            status="complete",
        )
        for candle in input.candles
    )
    required_warmup = _WARMUP_CANDLE_COUNTS[input.preset.strategy_type]
    if input.preset.strategy_type == "price_sma_cross":
        series = calculate_sma_series(strategy_candles)
        if series.status != "success":
            _raise_calculation_status(series.status)
        points_by_id = {point.candle_id: point for point in series.points}
        previous_point = points_by_id.get(input.candles[required_warmup - 1].candle_id)
        if previous_point is None:
            raise _ValidationFailure("invalid_input", "calculation_invariant")
        previous_left = input.candles[required_warmup - 1].close_price
        previous_right = previous_point.value
        observations: list[_SignalObservation] = []
        for analysis_sequence, candle_index in enumerate(
            range(required_warmup, len(input.candles))
        ):
            candle = input.candles[candle_index]
            point = points_by_id.get(candle.candle_id)
            if point is None:
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            current_left = candle.close_price
            current_right = point.value
            observations.append(
                _observation(
                    analysis_sequence=analysis_sequence,
                    candle_index=candle_index,
                    candle=candle,
                    previous_left=previous_left,
                    previous_right=previous_right,
                    current_left=current_left,
                    current_right=current_right,
                    direction=input.preset.direction,
                )
            )
            previous_left = current_left
            previous_right = current_right
        return tuple(observations)

    series = calculate_rsi_series(strategy_candles)
    if series.status != "success":
        _raise_calculation_status(series.status)
    points_by_id = {point.candle_id: point for point in series.points}
    previous_point = points_by_id.get(input.candles[required_warmup - 1].candle_id)
    if previous_point is None or input.preset.threshold is None:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    previous_left = previous_point.value
    previous_right = input.preset.threshold
    observations = []
    for analysis_sequence, candle_index in enumerate(
        range(required_warmup, len(input.candles))
    ):
        candle = input.candles[candle_index]
        point = points_by_id.get(candle.candle_id)
        if point is None:
            raise _ValidationFailure("invalid_input", "calculation_invariant")
        current_left = point.value
        current_right = input.preset.threshold
        observations.append(
            _observation(
                analysis_sequence=analysis_sequence,
                candle_index=candle_index,
                candle=candle,
                previous_left=previous_left,
                previous_right=previous_right,
                current_left=current_left,
                current_right=current_right,
                direction=input.preset.direction,
            )
        )
        previous_left = current_left
        previous_right = current_right
    return tuple(observations)


def _observation(
    *,
    analysis_sequence: int,
    candle_index: int,
    candle: HistoricalSimulationCandle,
    previous_left: Decimal,
    previous_right: Decimal,
    current_left: Decimal,
    current_right: Decimal,
    direction: SignalDirection,
) -> _SignalObservation:
    return _SignalObservation(
        analysis_sequence=analysis_sequence,
        candle_index=candle_index,
        candle=candle,
        signal_direction=direction,
        previous_left_value=previous_left,
        previous_right_value=previous_right,
        current_left_value=current_left,
        current_right_value=current_right,
        triggered=crosses(
            direction=direction,
            previous_left_value=previous_left,
            previous_right_value=previous_right,
            current_left_value=current_left,
            current_right_value=current_right,
        ),
    )


def _raise_calculation_status(status: str) -> None:
    if status == "insufficient_history":
        raise _ValidationFailure("insufficient_history", "missing_warmup")
    if status == "gap_detected":
        raise _ValidationFailure("gap_detected", "candle_gap")
    if status == "unsupported_version":
        raise _ValidationFailure("unsupported_calculation_version", "calculation_invariant")
    raise _ValidationFailure("invalid_input", "calculation_invariant")


def _simulate(
    input: _ValidatedSimulationInput,
    observations: tuple[_SignalObservation, ...],
) -> HistoricalSimulationResult:
    current_equity = input.assumptions.initial_equity
    gross_growth = Decimal("1")
    running_peak = current_equity
    active: _OpenTrade | None = None
    pending: _PendingTrade | None = None
    trades: list[HistoricalSimulationTrade] = []
    equity_series: list[HistoricalSimulationEquityPoint] = []
    signal_count = 0
    overlapping_signal_count = 0
    insufficient_forward_window_signal_count = 0
    equity_exhausted_signal_count = 0
    winning_trade_count = 0
    losing_trade_count = 0
    flat_trade_count = 0

    for observation in observations:
        candle_index = observation.candle_index
        candle = observation.candle
        if active is not None and active.pending.exit_index == candle_index:
            trade = _close_trade(active, candle, input.assumptions)
            trades.append(trade)
            current_equity = trade.equity_after
            gross_growth = _multiply(gross_growth, Decimal("1") + trade.gross_return)
            if trade.outcome == "win":
                winning_trade_count += 1
            elif trade.outcome == "loss":
                losing_trade_count += 1
            else:
                flat_trade_count += 1
            active = None
        elif active is not None and active.pending.exit_index < candle_index:
            raise _ValidationFailure("invalid_input", "calculation_invariant")

        if pending is not None:
            if pending.entry_index < candle_index:
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            if pending.entry_index == candle_index:
                if active is not None:
                    raise _ValidationFailure("invalid_input", "calculation_invariant")
                active = _open_trade(pending, candle, input.assumptions)
                pending = None

        if active is None:
            point_equity = current_equity
            position_state: PositionState = "flat"
            active_trade_sequence = None
        else:
            point_equity = _mark_to_market_equity(
                active,
                candle.close_price,
                input.assumptions,
            )
            position_state = (
                "long"
                if active.pending.signal.signal_direction == "cross_above"
                else "synthetic_short"
            )
            active_trade_sequence = active.pending.sequence
        running_peak = max(running_peak, point_equity)
        drawdown = _subtract(_divide(point_equity, running_peak), Decimal("1"))
        equity_series.append(
            HistoricalSimulationEquityPoint(
                sequence=observation.analysis_sequence,
                candle_id=candle.candle_id,
                candle_revision=candle.candle_revision,
                candle_open_time=candle.open_time,
                candle_close_time=candle.close_time,
                equity=point_equity,
                drawdown=drawdown,
                position_state=position_state,
                active_trade_sequence=active_trade_sequence,
            )
        )

        if not observation.triggered:
            continue
        signal_count += 1
        entry_index = candle_index + 1
        exit_index = entry_index + input.assumptions.holding_period_candles - 1
        if not _execution_window_inside_range(
            input.candles,
            entry_index=entry_index,
            exit_index=exit_index,
            analysis_start=input.analysis_start,
            analysis_end=input.analysis_end,
        ):
            insufficient_forward_window_signal_count += 1
        elif active is not None or pending is not None:
            overlapping_signal_count += 1
        elif current_equity <= Decimal("0"):
            equity_exhausted_signal_count += 1
        else:
            pending = _PendingTrade(
                sequence=len(trades) + 1,
                signal=observation,
                entry_index=entry_index,
                exit_index=exit_index,
                equity_before=current_equity,
            )

    if active is not None or pending is not None:
        raise _ValidationFailure("invalid_input", "calculation_invariant")

    summary = _summary(
        analysis_candle_count=len(observations),
        signal_count=signal_count,
        trades=tuple(trades),
        overlapping_signal_count=overlapping_signal_count,
        insufficient_forward_window_signal_count=insufficient_forward_window_signal_count,
        equity_exhausted_signal_count=equity_exhausted_signal_count,
        initial_equity=input.assumptions.initial_equity,
        final_equity=current_equity,
        gross_return=_subtract(gross_growth, Decimal("1")),
        equity_series=tuple(equity_series),
    )
    return HistoricalSimulationResult(
        status="success",
        failure_reason=None,
        dataset_fingerprint=input.dataset.manifest_fingerprint,
        preset_code=input.preset.code,
        preset_version=input.preset.version,
        calculation_version=input.calculation_version,
        engine_version=ENGINE_VERSION,
        assumption_version=ASSUMPTION_VERSION,
        analysis_start=input.analysis_start,
        analysis_end=input.analysis_end,
        assumptions=input.assumptions,
        trades=tuple(trades),
        equity_series=tuple(equity_series),
        summary=summary,
        safety_disclosures=SAFETY_DISCLOSURES,
        result_fingerprint=None,
    )


def _open_trade(
    pending: _PendingTrade,
    entry_candle: HistoricalSimulationCandle,
    assumptions: FixedHorizonAssumptions,
) -> _OpenTrade:
    if pending.signal.signal_direction == "cross_above":
        entry_fill_price = _multiply(
            entry_candle.open_price,
            Decimal("1") + assumptions.entry_slippage_rate,
        )
    else:
        entry_fill_price = _multiply(
            entry_candle.open_price,
            Decimal("1") - assumptions.entry_slippage_rate,
        )
    return _OpenTrade(
        pending=pending,
        entry_candle=entry_candle,
        entry_fill_price=entry_fill_price,
    )


def _close_trade(
    active: _OpenTrade,
    exit_candle: HistoricalSimulationCandle,
    assumptions: FixedHorizonAssumptions,
) -> HistoricalSimulationTrade:
    signal = active.pending.signal
    long_position = signal.signal_direction == "cross_above"
    if long_position:
        exit_fill_price = _multiply(
            exit_candle.close_price,
            Decimal("1") - assumptions.exit_slippage_rate,
        )
        gross_return = _subtract(
            _divide(exit_candle.close_price, active.entry_candle.open_price),
            Decimal("1"),
        )
        net_return_before_cap = _subtract(
            _subtract(
                _divide(exit_fill_price, active.entry_fill_price),
                Decimal("1"),
            ),
            _multiply(Decimal("2"), assumptions.fee_rate),
        )
        position_direction: PositionDirection = "long"
    else:
        exit_fill_price = _multiply(
            exit_candle.close_price,
            Decimal("1") + assumptions.exit_slippage_rate,
        )
        gross_return = _subtract(
            Decimal("1"),
            _divide(exit_candle.close_price, active.entry_candle.open_price),
        )
        net_return_before_cap = _subtract(
            _subtract(
                Decimal("1"),
                _divide(exit_fill_price, active.entry_fill_price),
            ),
            _multiply(Decimal("2"), assumptions.fee_rate),
        )
        position_direction = "synthetic_short"
    net_return = max(Decimal("-1"), net_return_before_cap)
    net_pnl = _multiply(active.pending.equity_before, net_return)
    equity_after = max(
        Decimal("0"),
        _add(active.pending.equity_before, net_pnl),
    )
    gross_pnl = _multiply(active.pending.equity_before, gross_return)
    if net_pnl > Decimal("0"):
        outcome: TradeOutcome = "win"
    elif net_pnl < Decimal("0"):
        outcome = "loss"
    else:
        outcome = "flat"
    return HistoricalSimulationTrade(
        sequence=active.pending.sequence,
        signal_candle_id=signal.candle.candle_id,
        signal_candle_revision=signal.candle.candle_revision,
        signal_open_time=signal.candle.open_time,
        signal_close_time=signal.candle.close_time,
        signal_direction=signal.signal_direction,
        position_direction=position_direction,
        entry_candle_id=active.entry_candle.candle_id,
        entry_candle_revision=active.entry_candle.candle_revision,
        entry_open_time=active.entry_candle.open_time,
        entry_raw_price=active.entry_candle.open_price,
        entry_fill_price=active.entry_fill_price,
        exit_candle_id=exit_candle.candle_id,
        exit_candle_revision=exit_candle.candle_revision,
        exit_close_time=exit_candle.close_time,
        exit_raw_price=exit_candle.close_price,
        exit_fill_price=exit_fill_price,
        holding_candle_count=assumptions.holding_period_candles,
        fee_rate=assumptions.fee_rate,
        slippage_rate=assumptions.entry_slippage_rate,
        equity_before=active.pending.equity_before,
        gross_return=gross_return,
        net_return=net_return,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        equity_after=equity_after,
        outcome=outcome,
    )


def _mark_to_market_equity(
    active: _OpenTrade,
    close_price: Decimal,
    assumptions: FixedHorizonAssumptions,
) -> Decimal:
    if active.pending.signal.signal_direction == "cross_above":
        exit_fill_price = _multiply(
            close_price,
            Decimal("1") - assumptions.exit_slippage_rate,
        )
        net_return_before_cap = _subtract(
            _subtract(
                _divide(exit_fill_price, active.entry_fill_price),
                Decimal("1"),
            ),
            _multiply(Decimal("2"), assumptions.fee_rate),
        )
    else:
        exit_fill_price = _multiply(
            close_price,
            Decimal("1") + assumptions.exit_slippage_rate,
        )
        net_return_before_cap = _subtract(
            _subtract(
                Decimal("1"),
                _divide(exit_fill_price, active.entry_fill_price),
            ),
            _multiply(Decimal("2"), assumptions.fee_rate),
        )
    net_return = max(Decimal("-1"), net_return_before_cap)
    return max(
        Decimal("0"),
        _add(
            active.pending.equity_before,
            _multiply(active.pending.equity_before, net_return),
        ),
    )


def _execution_window_inside_range(
    candles: tuple[HistoricalSimulationCandle, ...],
    *,
    entry_index: int,
    exit_index: int,
    analysis_start: datetime,
    analysis_end: datetime,
) -> bool:
    if entry_index < 0 or exit_index >= len(candles):
        return False
    entry_candle = candles[entry_index]
    exit_candle = candles[exit_index]
    return (
        analysis_start <= entry_candle.open_time < analysis_end
        and analysis_start <= exit_candle.open_time < analysis_end
        and exit_candle.close_time <= analysis_end
    )


def _summary(
    *,
    analysis_candle_count: int,
    signal_count: int,
    trades: tuple[HistoricalSimulationTrade, ...],
    overlapping_signal_count: int,
    insufficient_forward_window_signal_count: int,
    equity_exhausted_signal_count: int,
    initial_equity: Decimal,
    final_equity: Decimal,
    gross_return: Decimal,
    equity_series: tuple[HistoricalSimulationEquityPoint, ...],
) -> HistoricalSimulationSummary:
    positive_pnl = _sum_decimals(
        trade.net_pnl for trade in trades if trade.net_pnl > Decimal("0")
    )
    negative_pnl = _sum_decimals(
        trade.net_pnl for trade in trades if trade.net_pnl < Decimal("0")
    )
    if trades:
        win_rate = _divide(
            Decimal(sum(trade.outcome == "win" for trade in trades)),
            Decimal(len(trades)),
        )
        win_rate_reason = None
        if negative_pnl < Decimal("0"):
            profit_factor = _divide(positive_pnl, abs(negative_pnl))
            profit_factor_reason = None
        else:
            profit_factor = None
            profit_factor_reason: UndefinedMetricReason = "no_losing_trades"
    else:
        win_rate = None
        win_rate_reason = "no_trades"
        profit_factor = None
        profit_factor_reason = "no_trades"
    maximum_drawdown = min(
        (point.drawdown for point in equity_series),
        default=Decimal("0"),
    )
    return HistoricalSimulationSummary(
        analysis_candle_count=analysis_candle_count,
        signal_count=signal_count,
        executed_trade_count=len(trades),
        winning_trade_count=sum(trade.outcome == "win" for trade in trades),
        losing_trade_count=sum(trade.outcome == "loss" for trade in trades),
        flat_trade_count=sum(trade.outcome == "flat" for trade in trades),
        overlapping_signal_count=overlapping_signal_count,
        insufficient_forward_window_signal_count=insufficient_forward_window_signal_count,
        equity_exhausted_signal_count=equity_exhausted_signal_count,
        initial_equity=initial_equity,
        final_equity=final_equity,
        gross_return=gross_return,
        net_return=_subtract(_divide(final_equity, initial_equity), Decimal("1")),
        maximum_drawdown=maximum_drawdown,
        win_rate=win_rate,
        win_rate_undefined_reason=win_rate_reason,
        profit_factor=profit_factor,
        profit_factor_undefined_reason=profit_factor_reason,
    )


def _failure_result(
    input: object,
    status: SimulationStatus,
    reason: FailureReason,
) -> HistoricalSimulationResult:
    dataset_fingerprint: str | None = None
    preset_code: str | None = None
    preset_version: int | None = None
    calculation_version: str | None = None
    engine_version: str | None = None
    assumption_version: str | None = None
    analysis_start: datetime | None = None
    analysis_end: datetime | None = None
    if isinstance(input, HistoricalSimulationInput):
        dataset = input.dataset
        preset = input.preset
        if isinstance(dataset, HistoricalDatasetManifest):
            if isinstance(dataset.manifest_fingerprint, str):
                dataset_fingerprint = dataset.manifest_fingerprint
        if isinstance(preset, HistoricalPresetSnapshot):
            preset_code = preset.code if isinstance(preset.code, str) else None
            preset_version = preset.version if isinstance(preset.version, int) else None
        calculation_version = (
            input.calculation_version
            if isinstance(input.calculation_version, str)
            else None
        )
        engine_version = input.engine_version if isinstance(input.engine_version, str) else None
        assumption_version = (
            input.assumption_version if isinstance(input.assumption_version, str) else None
        )
        analysis_start = _safe_utc_datetime(input.analysis_start)
        analysis_end = _safe_utc_datetime(input.analysis_end)
    return HistoricalSimulationResult(
        status=status,
        failure_reason=reason,
        dataset_fingerprint=dataset_fingerprint,
        preset_code=preset_code,
        preset_version=preset_version,
        calculation_version=calculation_version,
        engine_version=engine_version,
        assumption_version=assumption_version,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        assumptions=None,
        trades=(),
        equity_series=(),
        summary=None,
        safety_disclosures=SAFETY_DISCLOSURES,
        result_fingerprint=None,
    )


def _result_fingerprint(result: HistoricalSimulationResult) -> str:
    payload = {
        "schema_version": RESULT_FINGERPRINT_SCHEMA_VERSION,
        "dataset_fingerprint": result.dataset_fingerprint,
        "preset_code": result.preset_code,
        "preset_version": result.preset_version,
        "calculation_version": result.calculation_version,
        "engine_version": result.engine_version,
        "assumption_version": result.assumption_version,
        "analysis_start": _optional_utc_z(result.analysis_start),
        "analysis_end": _optional_utc_z(result.analysis_end),
        "assumptions": _assumptions_payload(result.assumptions),
        "trades": [_trade_payload(trade) for trade in result.trades],
        "equity_series": [
            _equity_point_payload(point) for point in result.equity_series
        ],
        "summary": _summary_payload(result.summary),
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _assumptions_payload(
    assumptions: FixedHorizonAssumptions | None,
) -> dict[str, object] | None:
    if assumptions is None:
        return None
    return {
        "initial_equity": _display_decimal(assumptions.initial_equity),
        "signal_timing": assumptions.signal_timing,
        "entry_timing": assumptions.entry_timing,
        "holding_period_candles": assumptions.holding_period_candles,
        "position_direction": assumptions.position_direction,
        "position_sizing": assumptions.position_sizing,
        "concurrent_positions": assumptions.concurrent_positions,
        "overlapping_signals": assumptions.overlapping_signals,
        "entry_slippage_rate": _display_decimal(assumptions.entry_slippage_rate),
        "exit_slippage_rate": _display_decimal(assumptions.exit_slippage_rate),
        "fee_rate": _display_decimal(assumptions.fee_rate),
        "stop_loss": assumptions.stop_loss,
        "take_profit": assumptions.take_profit,
        "early_exit": assumptions.early_exit,
        "end_of_range": assumptions.end_of_range,
        "compounding": assumptions.compounding,
        "short_loss_cap": assumptions.short_loss_cap,
    }


def _trade_payload(trade: HistoricalSimulationTrade) -> dict[str, object]:
    return {
        "sequence": trade.sequence,
        "signal_candle_id": str(trade.signal_candle_id),
        "signal_candle_revision": trade.signal_candle_revision,
        "signal_open_time": _utc_z(trade.signal_open_time),
        "signal_close_time": _utc_z(trade.signal_close_time),
        "signal_direction": trade.signal_direction,
        "position_direction": trade.position_direction,
        "entry_candle_id": str(trade.entry_candle_id),
        "entry_candle_revision": trade.entry_candle_revision,
        "entry_open_time": _utc_z(trade.entry_open_time),
        "entry_raw_price": _display_decimal(trade.entry_raw_price),
        "entry_fill_price": _display_decimal(trade.entry_fill_price),
        "exit_candle_id": str(trade.exit_candle_id),
        "exit_candle_revision": trade.exit_candle_revision,
        "exit_close_time": _utc_z(trade.exit_close_time),
        "exit_raw_price": _display_decimal(trade.exit_raw_price),
        "exit_fill_price": _display_decimal(trade.exit_fill_price),
        "holding_candle_count": trade.holding_candle_count,
        "fee_rate": _display_decimal(trade.fee_rate),
        "slippage_rate": _display_decimal(trade.slippage_rate),
        "equity_before": _display_decimal(trade.equity_before),
        "gross_return": _display_decimal(trade.gross_return),
        "net_return": _display_decimal(trade.net_return),
        "gross_pnl": _display_decimal(trade.gross_pnl),
        "net_pnl": _display_decimal(trade.net_pnl),
        "equity_after": _display_decimal(trade.equity_after),
        "outcome": trade.outcome,
    }


def _equity_point_payload(point: HistoricalSimulationEquityPoint) -> dict[str, object]:
    return {
        "sequence": point.sequence,
        "candle_id": str(point.candle_id),
        "candle_revision": point.candle_revision,
        "candle_open_time": _utc_z(point.candle_open_time),
        "candle_close_time": _utc_z(point.candle_close_time),
        "equity": _display_decimal(point.equity),
        "drawdown": _display_decimal(point.drawdown),
        "position_state": point.position_state,
        "active_trade_sequence": point.active_trade_sequence,
    }


def _summary_payload(summary: HistoricalSimulationSummary | None) -> dict[str, object] | None:
    if summary is None:
        return None
    return {
        "analysis_candle_count": summary.analysis_candle_count,
        "signal_count": summary.signal_count,
        "executed_trade_count": summary.executed_trade_count,
        "winning_trade_count": summary.winning_trade_count,
        "losing_trade_count": summary.losing_trade_count,
        "flat_trade_count": summary.flat_trade_count,
        "overlapping_signal_count": summary.overlapping_signal_count,
        "insufficient_forward_window_signal_count": (
            summary.insufficient_forward_window_signal_count
        ),
        "equity_exhausted_signal_count": summary.equity_exhausted_signal_count,
        "initial_equity": _display_decimal(summary.initial_equity),
        "final_equity": _display_decimal(summary.final_equity),
        "gross_return": _display_decimal(summary.gross_return),
        "net_return": _display_decimal(summary.net_return),
        "maximum_drawdown": _display_decimal(summary.maximum_drawdown),
        "win_rate": _optional_display_decimal(summary.win_rate),
        "win_rate_undefined_reason": summary.win_rate_undefined_reason,
        "profit_factor": _optional_display_decimal(summary.profit_factor),
        "profit_factor_undefined_reason": summary.profit_factor_undefined_reason,
    }


def _normalize_utc_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("UTC timestamp required")
    return value.astimezone(UTC)


def _safe_utc_datetime(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    try:
        return _normalize_utc_datetime(value)
    except (AttributeError, TypeError, ValueError):
        return None


def _is_timeframe_boundary(value: datetime, timeframe: Timeframe) -> bool:
    return (
        value.minute == 0
        and value.second == 0
        and value.microsecond == 0
        and value.hour % _TIMEFRAME_HOURS[timeframe] == 0
    )


def _is_decimal(value: object, *, positive: bool) -> bool:
    if not isinstance(value, Decimal) or not value.is_finite():
        return False
    return value > Decimal("0") if positive else value >= Decimal("0")


def _is_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _utc_z(value: datetime) -> str:
    return _normalize_utc_datetime(value).isoformat(timespec="microseconds").replace(
        "+00:00",
        "Z",
    )


def _optional_utc_z(value: datetime | None) -> str | None:
    return None if value is None else _utc_z(value)


def _display_decimal(value: Decimal) -> str:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        quantized = value.quantize(DISPLAY_QUANTUM)
    return format(quantized, "f")


def _optional_display_decimal(value: Decimal | None) -> str | None:
    return None if value is None else _display_decimal(value)


def _add(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return left + right


def _subtract(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return left - right


def _multiply(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return left * right


def _divide(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return left / right


def _sum_decimals(values: Iterable[Decimal]) -> Decimal:
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        context.rounding = ROUND_HALF_EVEN
        total = Decimal("0")
        for value in values:
            total += value
        return total
