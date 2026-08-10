"""Pure deterministic simulation for configurable long-only exits."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from freecoinalert_api.historical_analysis.engine import (
    CONFIGURABLE_ASSUMPTION_VERSION,
    CONFIGURABLE_ENGINE_VERSION,
    CONFIGURABLE_ENGINE_VERSIONS,
    ConfigurableExitAssumptions,
    CONFIGURABLE_EXIT_V2_ASSUMPTIONS,
    CONFIGURABLE_EXIT_V1_ASSUMPTIONS,
    CONFIGURABLE_RESULT_FINGERPRINT_SCHEMA_VERSION,
    LEGACY_ASSUMPTION_VERSION,
    LEGACY_CONFIGURABLE_ASSUMPTION_VERSION,
    LEGACY_CONFIGURABLE_ENGINE_VERSION,
    LEGACY_CONFIGURABLE_RESULT_FINGERPRINT_SCHEMA_VERSION,
    LEGACY_ENGINE_VERSION,
    FIXED_HORIZON_V1_ASSUMPTIONS,
    HistoricalDatasetManifest,
    HistoricalPresetSnapshot,
    HistoricalSimulationCandle,
    HistoricalSimulationEquityPoint,
    HistoricalSimulationInput,
    HistoricalSimulationResult,
    HistoricalSimulationSummary,
    HistoricalSimulationTrade,
    SAFETY_DISCLOSURES,
    _ValidatedSimulationInput,
    _ValidationFailure,
    _assumptions_payload,
    _configurable_trade_payload,
    _equity_point_payload,
    _execution_window_inside_range,
    _entry_candle_inside_range,
    _is_fingerprint,
    _normalize_utc_datetime,
    _observation,
    _raise_calculation_status,
    _summary,
    _summary_payload,
    _utc_z,
    _validate_input,
)
from freecoinalert_api.signals.crossings import crosses
from freecoinalert_api.historical_analysis.strategy import (
    CONFIGURABLE_STRATEGY_VERSION,
    STRATEGY_SNAPSHOT_SCHEMA_VERSION,
)
from freecoinalert_api.strategies import (
    StrategyCandle,
    calculate_rsi_series,
    calculate_sma_series,
)
from freecoinalert_api.strategies.errors import StrategyCalculationError


ExitReason = Literal[
    "stop_loss_percent",
    "take_profit_percent",
    "rsi_threshold_cross",
    "max_holding_candles",
]
ExitPriceBasis = Literal[
    "stop_loss_level",
    "take_profit_level",
    "gap_open",
    "confirmed_candle_close",
]


@dataclass(frozen=True, slots=True)
class ConfigurableSimulationInput:
    """Immutable input for one versioned configurable-exit simulation."""

    dataset: HistoricalDatasetManifest
    preset: HistoricalPresetSnapshot
    calculation_version: str
    analysis_start: datetime
    analysis_end: datetime
    candles: tuple[HistoricalSimulationCandle, ...]
    strategy_version: str
    strategy_fingerprint: str
    strategy_snapshot: Mapping[str, object]
    engine_version: str = CONFIGURABLE_ENGINE_VERSION
    assumption_version: str = CONFIGURABLE_ASSUMPTION_VERSION


@dataclass(frozen=True, slots=True)
class _ExitRule:
    type: ExitReason
    percent: Decimal | None = None
    direction: Literal["cross_above", "cross_below"] | None = None
    threshold: Decimal | None = None
    candles: int | None = None
    snapshot: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class _PendingTrade:
    sequence: int
    signal: object
    entry_index: int
    equity_before: Decimal


@dataclass(frozen=True, slots=True)
class _OpenTrade:
    pending: _PendingTrade
    entry_candle: HistoricalSimulationCandle
    entry_fill_price: Decimal


def simulate_configurable_exit(
    input: ConfigurableSimulationInput,
) -> HistoricalSimulationResult:
    """Simulate a normalized long-only strategy over immutable candles."""

    try:
        validated, rules, strategy_snapshot = _validate_configurable_input(input)
        observations, rsi_values = _calculate_configurable_observations(
            validated,
            rules=rules,
        )
        result = _simulate_configurable(
            input=input,
            validated=validated,
            observations=observations,
            rsi_values=rsi_values,
            rules=rules,
            strategy_snapshot=strategy_snapshot,
        )
        return replace(
            result,
            result_fingerprint=_result_fingerprint_v2(result),
        )
    except _ValidationFailure as failure:
        return _failure_result(input, failure.status, failure.reason)
    except (ArithmeticError, AttributeError, KeyError, TypeError, ValueError):
        return _failure_result(input, "invalid_input", "calculation_invariant")
    except StrategyCalculationError:
        return _failure_result(input, "invalid_input", "calculation_invariant")


def _validate_configurable_input(
    input: ConfigurableSimulationInput,
) -> tuple[
    _ValidatedSimulationInput,
    tuple[_ExitRule, ...],
    dict[str, object],
]:
    if not isinstance(input, ConfigurableSimulationInput):
        raise _ValidationFailure("invalid_input", "input_type_invalid")
    if input.engine_version not in CONFIGURABLE_ENGINE_VERSIONS:
        raise _ValidationFailure(
            "unsupported_engine_version",
            "calculation_invariant",
        )
    expected_assumption_version = (
        LEGACY_CONFIGURABLE_ASSUMPTION_VERSION
        if input.engine_version == LEGACY_CONFIGURABLE_ENGINE_VERSION
        else CONFIGURABLE_ASSUMPTION_VERSION
    )
    if input.assumption_version != expected_assumption_version:
        raise _ValidationFailure(
            "unsupported_assumption_version",
            "calculation_invariant",
        )

    legacy_input = HistoricalSimulationInput(
        dataset=input.dataset,
        preset=input.preset,
        calculation_version=input.calculation_version,
        analysis_start=input.analysis_start,
        analysis_end=input.analysis_end,
        candles=input.candles,
        engine_version=LEGACY_ENGINE_VERSION,
        assumption_version=LEGACY_ASSUMPTION_VERSION,
        assumptions=FIXED_HORIZON_V1_ASSUMPTIONS,
    )
    validated = _validate_input(legacy_input)
    if input.strategy_version != CONFIGURABLE_STRATEGY_VERSION:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    if not _is_fingerprint(input.strategy_fingerprint):
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    rules, strategy_snapshot = _normalize_strategy_snapshot(
        input.strategy_snapshot,
        preset=input.preset,
        calculation_version=input.calculation_version,
        timeframe=validated.preset.timeframe,
    )
    if input.strategy_fingerprint != _strategy_fingerprint(strategy_snapshot):
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    return validated, rules, strategy_snapshot


def _normalize_strategy_snapshot(
    raw_snapshot: Mapping[str, object],
    *,
    preset: HistoricalPresetSnapshot,
    calculation_version: str,
    timeframe: str,
) -> tuple[tuple[_ExitRule, ...], dict[str, object]]:
    if not isinstance(raw_snapshot, Mapping):
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    if raw_snapshot.get("schema_version") != STRATEGY_SNAPSHOT_SCHEMA_VERSION:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    if raw_snapshot.get("version") != CONFIGURABLE_STRATEGY_VERSION:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    entry = raw_snapshot.get("entry")
    if not isinstance(entry, Mapping):
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    if entry != {
        "preset_code": preset.code,
        "preset_version": preset.version,
        "timeframe": timeframe,
        "signal_direction": preset.direction,
        "calculation_version": calculation_version,
    }:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    if raw_snapshot.get("position_direction") != "long":
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    raw_rules = raw_snapshot.get("exit_rules")
    if not isinstance(raw_rules, list) or not 1 <= len(raw_rules) <= 4:
        raise _ValidationFailure("invalid_input", "calculation_invariant")

    parsed: dict[ExitReason, _ExitRule] = {}
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, Mapping):
            raise _ValidationFailure("invalid_input", "calculation_invariant")
        rule_type = raw_rule.get("type")
        if rule_type in {"take_profit_percent", "stop_loss_percent"}:
            if rule_type in parsed:
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            raw_percent = raw_rule.get("percent")
            if not isinstance(raw_percent, str):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            percent = _strict_decimal(raw_percent)
            if percent is None or percent < Decimal("0.01"):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            if rule_type == "take_profit_percent" and percent > Decimal("1000"):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            if rule_type == "stop_loss_percent" and percent >= Decimal("100"):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            parsed[rule_type] = _ExitRule(
                type=rule_type,
                percent=percent,
                snapshot={
                    "type": rule_type,
                    "percent": raw_percent,
                },
            )
        elif rule_type == "rsi_threshold_cross":
            if rule_type in parsed:
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            direction = raw_rule.get("direction")
            raw_threshold = raw_rule.get("threshold")
            if not isinstance(raw_threshold, str):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            threshold = _strict_decimal(raw_threshold)
            if direction not in {"cross_above", "cross_below"}:
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            if threshold is None or not Decimal("0") < threshold < Decimal("100"):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            if (
                raw_rule.get("period") != 14
                or raw_rule.get("price_input") != "close"
                or raw_rule.get("timeframe") != timeframe
                or raw_rule.get("calculation_version") != "rsi_wilder_close_v1"
            ):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            parsed[rule_type] = _ExitRule(
                type=rule_type,
                direction=direction,
                threshold=threshold,
                snapshot={
                    "type": rule_type,
                    "period": 14,
                    "direction": direction,
                    "threshold": raw_threshold,
                    "price_input": "close",
                    "timeframe": timeframe,
                    "calculation_version": "rsi_wilder_close_v1",
                },
            )
        elif rule_type == "max_holding_candles":
            if rule_type in parsed:
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            candles = raw_rule.get("candles")
            if (
                not isinstance(candles, int)
                or isinstance(candles, bool)
                or candles < 1
                or candles > 2_200
            ):
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            parsed[rule_type] = _ExitRule(
                type=rule_type,
                candles=candles,
                snapshot={"type": rule_type, "candles": candles},
            )
        else:
            raise _ValidationFailure("invalid_input", "calculation_invariant")

    if "max_holding_candles" not in parsed:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    ordered = tuple(
        parsed[rule_type]
        for rule_type in (
            "stop_loss_percent",
            "take_profit_percent",
            "rsi_threshold_cross",
            "max_holding_candles",
        )
        if rule_type in parsed
    )
    return ordered, {
        "schema_version": STRATEGY_SNAPSHOT_SCHEMA_VERSION,
        "version": CONFIGURABLE_STRATEGY_VERSION,
        "entry": dict(entry),
        "position_direction": "long",
        "exit_rules": [rule.snapshot for rule in ordered],
    }


def _calculate_configurable_observations(
    input: _ValidatedSimulationInput,
    *,
    rules: tuple[_ExitRule, ...],
) -> tuple[tuple[object, ...], dict[object, Decimal]]:
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
    rsi_values: dict[object, Decimal] = {}
    rsi_rule = next((rule for rule in rules if rule.type == "rsi_threshold_cross"), None)
    rsi_series = None
    if input.preset.strategy_type == "rsi_threshold_cross" or rsi_rule is not None:
        rsi_series = calculate_rsi_series(strategy_candles)
        if rsi_series.status != "success":
            _raise_calculation_status(rsi_series.status)
        rsi_values = {point.candle_id: point.value for point in rsi_series.points}

    if input.preset.strategy_type == "price_sma_cross":
        series = calculate_sma_series(strategy_candles)
        if series.status != "success":
            _raise_calculation_status(series.status)
        points_by_id = {point.candle_id: point for point in series.points}
        required_warmup = 200
        previous_point = points_by_id.get(input.candles[required_warmup - 1].candle_id)
        if previous_point is None:
            raise _ValidationFailure("invalid_input", "calculation_invariant")
        previous_left = input.candles[required_warmup - 1].close_price
        previous_right = previous_point.value
        observations = []
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
        return tuple(observations), rsi_values

    points_by_id = rsi_values
    required_warmup = 15
    previous_candle = input.candles[required_warmup - 1]
    previous_left = points_by_id.get(previous_candle.candle_id)
    if previous_left is None:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    if input.preset.threshold is None:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    previous_right = input.preset.threshold
    observations = []
    for analysis_sequence, candle_index in enumerate(
        range(required_warmup, len(input.candles))
    ):
        candle = input.candles[candle_index]
        current_left = points_by_id.get(candle.candle_id)
        if current_left is None:
            raise _ValidationFailure("invalid_input", "calculation_invariant")
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
    return tuple(observations), rsi_values


def _simulate_configurable(
    *,
    input: ConfigurableSimulationInput,
    validated: _ValidatedSimulationInput,
    observations: tuple[object, ...],
    rsi_values: dict[object, Decimal],
    rules: tuple[_ExitRule, ...],
    strategy_snapshot: dict[str, object],
) -> HistoricalSimulationResult:
    legacy_behavior = input.engine_version == LEGACY_CONFIGURABLE_ENGINE_VERSION
    assumptions = (
        CONFIGURABLE_EXIT_V1_ASSUMPTIONS
        if legacy_behavior
        else CONFIGURABLE_EXIT_V2_ASSUMPTIONS
    )
    current_equity = assumptions.initial_equity
    gross_growth = Decimal("1")
    running_peak = current_equity
    active: _OpenTrade | None = None
    pending: _PendingTrade | None = None
    trades: list[HistoricalSimulationTrade] = []
    equity_series: list[HistoricalSimulationEquityPoint] = []
    signal_count = 0
    overlapping_signal_count = 0
    insufficient_forward_window_signal_count = 0
    entry_unavailable_signal_count = 0
    equity_exhausted_signal_count = 0
    max_holding = next(
        rule.candles for rule in rules if rule.type == "max_holding_candles"
    )

    for observation in observations:
        candle_index = observation.candle_index
        candle = observation.candle
        if pending is not None:
            if pending.entry_index < candle_index:
                raise _ValidationFailure("invalid_input", "calculation_invariant")
            if pending.entry_index == candle_index:
                if active is not None:
                    raise _ValidationFailure("invalid_input", "calculation_invariant")
                active = _open_trade(pending, candle, assumptions)
                pending = None

        if active is not None:
            holding_count = candle_index - active.pending.entry_index + 1
            decision = _exit_decision(
                active=active,
                candle=candle,
                previous_candle=(
                    validated.candles[candle_index - 1]
                    if candle_index > 0
                    else None
                ),
                holding_count=holding_count,
                rsi_values=rsi_values,
                rules=rules,
            )
            if decision is not None:
                trade = _close_trade(
                    active,
                    candle,
                    holding_count,
                    decision,
                    assumptions,
                )
                trades.append(trade)
                current_equity = trade.equity_after
                gross_growth = _multiply(gross_growth, Decimal("1") + trade.gross_return)
                active = None

        if active is None:
            point_equity = current_equity
            position_state = "flat"
            active_trade_sequence = None
        else:
            point_equity = _mark_to_market_equity(
                active,
                candle.close_price,
                assumptions,
            )
            position_state = "long"
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
        if legacy_behavior:
            exit_index = entry_index + max_holding - 1
            if not _execution_window_inside_range(
                input.candles,
                entry_index=entry_index,
                exit_index=exit_index,
                analysis_start=validated.analysis_start,
                analysis_end=validated.analysis_end,
            ):
                insufficient_forward_window_signal_count += 1
                continue
        elif not _entry_candle_inside_range(
            input.candles,
            entry_index=entry_index,
            analysis_start=validated.analysis_start,
            analysis_end=validated.analysis_end,
        ):
            entry_unavailable_signal_count += 1
            continue

        if active is not None or pending is not None:
            overlapping_signal_count += 1
        elif current_equity <= Decimal("0"):
            equity_exhausted_signal_count += 1
        else:
            pending = _PendingTrade(
                sequence=len(trades) + 1,
                signal=observation,
                entry_index=entry_index,
                equity_before=current_equity,
            )

    if pending is not None:
        raise _ValidationFailure("invalid_input", "calculation_invariant")
    if active is not None:
        if legacy_behavior:
            raise _ValidationFailure("invalid_input", "calculation_invariant")
        final_candle = observations[-1].candle
        open_trade = _mark_to_market_trade(active, final_candle, assumptions)
        trades.append(open_trade)
        current_equity = open_trade.equity_after
        gross_growth = _multiply(
            gross_growth,
            Decimal("1") + open_trade.gross_return,
        )

    summary = _summary(
        analysis_candle_count=len(observations),
        signal_count=signal_count,
        trades=tuple(trades),
        overlapping_signal_count=overlapping_signal_count,
        insufficient_forward_window_signal_count=insufficient_forward_window_signal_count,
        entry_unavailable_signal_count=entry_unavailable_signal_count,
        equity_exhausted_signal_count=equity_exhausted_signal_count,
        initial_equity=assumptions.initial_equity,
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
        engine_version=input.engine_version,
        assumption_version=input.assumption_version,
        analysis_start=input.analysis_start,
        analysis_end=input.analysis_end,
        assumptions=assumptions,
        trades=tuple(trades),
        equity_series=tuple(equity_series),
        summary=summary,
        safety_disclosures=SAFETY_DISCLOSURES,
        result_fingerprint=None,
        strategy_version=input.strategy_version,
        strategy_fingerprint=input.strategy_fingerprint,
        strategy_snapshot=strategy_snapshot,
    )


def _exit_decision(
    *,
    active: _OpenTrade,
    candle: HistoricalSimulationCandle,
    previous_candle: HistoricalSimulationCandle | None,
    holding_count: int,
    rsi_values: dict[object, Decimal],
    rules: tuple[_ExitRule, ...],
) -> tuple[ExitReason, ExitPriceBasis, Decimal, dict[str, object]] | None:
    entry_raw_price = active.entry_candle.open_price
    for rule in rules:
        if rule.type == "stop_loss_percent":
            assert rule.percent is not None
            level = _multiply(
                entry_raw_price,
                Decimal("1") - rule.percent / Decimal("100"),
            )
            if candle.open_price < level:
                return rule.type, "gap_open", candle.open_price, rule.snapshot or {}
            if candle.low_price <= level:
                return rule.type, "stop_loss_level", level, rule.snapshot or {}
        elif rule.type == "take_profit_percent":
            assert rule.percent is not None
            level = _multiply(
                entry_raw_price,
                Decimal("1") + rule.percent / Decimal("100"),
            )
            if candle.high_price >= level:
                return rule.type, "take_profit_level", level, rule.snapshot or {}
        elif rule.type == "rsi_threshold_cross":
            assert rule.direction is not None
            assert rule.threshold is not None
            current_value = rsi_values.get(candle.candle_id)
            previous_value = (
                None
                if previous_candle is None
                else rsi_values.get(previous_candle.candle_id)
            )
            if current_value is None or previous_value is None:
                continue
            if crosses(
                direction=rule.direction,
                previous_left_value=previous_value,
                previous_right_value=rule.threshold,
                current_left_value=current_value,
                current_right_value=rule.threshold,
            ):
                return (
                    rule.type,
                    "confirmed_candle_close",
                    candle.close_price,
                    rule.snapshot or {},
                )
        elif rule.type == "max_holding_candles":
            assert rule.candles is not None
            if holding_count >= rule.candles:
                return (
                    rule.type,
                    "confirmed_candle_close",
                    candle.close_price,
                    rule.snapshot or {},
                )
    return None


def _open_trade(
    pending: _PendingTrade,
    candle: HistoricalSimulationCandle,
    assumptions: ConfigurableExitAssumptions,
) -> _OpenTrade:
    return _OpenTrade(
        pending=pending,
        entry_candle=candle,
        entry_fill_price=_multiply(
            candle.open_price,
            Decimal("1") + assumptions.entry_slippage_rate,
        ),
    )


def _close_trade(
    active: _OpenTrade,
    candle: HistoricalSimulationCandle,
    holding_count: int,
    decision: tuple[ExitReason, ExitPriceBasis, Decimal, dict[str, object]],
    assumptions: ConfigurableExitAssumptions,
) -> HistoricalSimulationTrade:
    exit_reason, exit_price_basis, exit_raw_price, exit_rule_snapshot = decision
    entry_raw_price = active.entry_candle.open_price
    exit_fill_price = _multiply(
        exit_raw_price,
        Decimal("1") - assumptions.exit_slippage_rate,
    )
    gross_return = _subtract(_divide(exit_raw_price, entry_raw_price), Decimal("1"))
    net_return_before_cap = _subtract(
        _subtract(
            _divide(exit_fill_price, active.entry_fill_price),
            Decimal("1"),
        ),
        _multiply(Decimal("2"), assumptions.fee_rate),
    )
    net_return = max(Decimal("-1"), net_return_before_cap)
    equity_before = active.pending.equity_before
    net_pnl = _multiply(equity_before, net_return)
    equity_after = max(Decimal("0"), _add(equity_before, net_pnl))
    gross_pnl = _multiply(equity_before, gross_return)
    if net_pnl > Decimal("0"):
        outcome = "win"
    elif net_pnl < Decimal("0"):
        outcome = "loss"
    else:
        outcome = "flat"
    signal = active.pending.signal
    return HistoricalSimulationTrade(
        trade_status="closed",
        sequence=active.pending.sequence,
        signal_candle_id=signal.candle.candle_id,
        signal_candle_revision=signal.candle.candle_revision,
        signal_open_time=signal.candle.open_time,
        signal_close_time=signal.candle.close_time,
        signal_direction=signal.signal_direction,
        position_direction="long",
        entry_candle_id=active.entry_candle.candle_id,
        entry_candle_revision=active.entry_candle.candle_revision,
        entry_open_time=active.entry_candle.open_time,
        entry_raw_price=entry_raw_price,
        entry_fill_price=active.entry_fill_price,
        exit_candle_id=candle.candle_id,
        exit_candle_revision=candle.candle_revision,
        exit_close_time=candle.close_time,
        exit_raw_price=exit_raw_price,
        exit_fill_price=exit_fill_price,
        holding_candle_count=holding_count,
        fee_rate=assumptions.fee_rate,
        slippage_rate=assumptions.entry_slippage_rate,
        equity_before=equity_before,
        gross_return=gross_return,
        net_return=net_return,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        equity_after=equity_after,
        outcome=outcome,
        mark_candle_id=None,
        mark_candle_revision=None,
        mark_close_time=None,
        mark_price=None,
        unrealized_return=None,
        unrealized_pnl=None,
        exit_reason=exit_reason,
        exit_price_basis=exit_price_basis,
        exit_rule_snapshot=exit_rule_snapshot,
    )


def _mark_to_market_equity(
    active: _OpenTrade,
    close_price: Decimal,
    assumptions: ConfigurableExitAssumptions,
) -> Decimal:
    if assumptions.end_of_range == "incomplete_trade_not_opened":
        mark_fill_price = _multiply(
            close_price,
            Decimal("1") - assumptions.exit_slippage_rate,
        )
        net_return_before_cap = _subtract(
            _subtract(
                _divide(mark_fill_price, active.entry_fill_price),
                Decimal("1"),
            ),
            _multiply(Decimal("2"), assumptions.fee_rate),
        )
    else:
        net_return_before_cap = _subtract(
            _subtract(
                _divide(close_price, active.entry_fill_price),
                Decimal("1"),
            ),
            assumptions.fee_rate,
        )
    net_return = max(Decimal("-1"), net_return_before_cap)
    return max(
        Decimal("0"),
        _add(
            active.pending.equity_before,
            _multiply(active.pending.equity_before, net_return),
        ),
    )


def _mark_to_market_trade(
    active: _OpenTrade,
    mark_candle: HistoricalSimulationCandle,
    assumptions: ConfigurableExitAssumptions,
) -> HistoricalSimulationTrade:
    entry_raw_price = active.entry_candle.open_price
    gross_return = _subtract(
        _divide(mark_candle.close_price, entry_raw_price),
        Decimal("1"),
    )
    net_return_before_cap = _subtract(
        _subtract(
            _divide(mark_candle.close_price, active.entry_fill_price),
            Decimal("1"),
        ),
        assumptions.fee_rate,
    )
    net_return = max(Decimal("-1"), net_return_before_cap)
    equity_before = active.pending.equity_before
    net_pnl = _multiply(equity_before, net_return)
    equity_after = max(Decimal("0"), _add(equity_before, net_pnl))
    gross_pnl = _multiply(equity_before, gross_return)
    signal = active.pending.signal
    return HistoricalSimulationTrade(
        trade_status="open_at_end",
        sequence=active.pending.sequence,
        signal_candle_id=signal.candle.candle_id,
        signal_candle_revision=signal.candle.candle_revision,
        signal_open_time=signal.candle.open_time,
        signal_close_time=signal.candle.close_time,
        signal_direction=signal.signal_direction,
        position_direction="long",
        entry_candle_id=active.entry_candle.candle_id,
        entry_candle_revision=active.entry_candle.candle_revision,
        entry_open_time=active.entry_candle.open_time,
        entry_raw_price=entry_raw_price,
        entry_fill_price=active.entry_fill_price,
        exit_candle_id=None,
        exit_candle_revision=None,
        exit_close_time=None,
        exit_raw_price=None,
        exit_fill_price=None,
        holding_candle_count=(
            mark_candle.position - active.entry_candle.position + 1
        ),
        fee_rate=assumptions.fee_rate,
        slippage_rate=assumptions.entry_slippage_rate,
        equity_before=equity_before,
        gross_return=gross_return,
        net_return=net_return,
        gross_pnl=gross_pnl,
        net_pnl=net_pnl,
        equity_after=equity_after,
        outcome=None,
        mark_candle_id=mark_candle.candle_id,
        mark_candle_revision=mark_candle.candle_revision,
        mark_close_time=mark_candle.close_time,
        mark_price=mark_candle.close_price,
        unrealized_return=net_return,
        unrealized_pnl=net_pnl,
        exit_reason=None,
        exit_price_basis=None,
        exit_rule_snapshot=None,
    )


def _result_fingerprint_v2(result: HistoricalSimulationResult) -> str:
    payload = {
        "schema_version": (
            LEGACY_CONFIGURABLE_RESULT_FINGERPRINT_SCHEMA_VERSION
            if result.engine_version == LEGACY_CONFIGURABLE_ENGINE_VERSION
            else CONFIGURABLE_RESULT_FINGERPRINT_SCHEMA_VERSION
        ),
        "dataset_fingerprint": result.dataset_fingerprint,
        "preset_code": result.preset_code,
        "preset_version": result.preset_version,
        "calculation_version": result.calculation_version,
        "engine_version": result.engine_version,
        "assumption_version": result.assumption_version,
        "strategy_version": result.strategy_version,
        "strategy_fingerprint": result.strategy_fingerprint,
        "strategy_snapshot": result.strategy_snapshot,
        "analysis_start": _optional_utc_z(result.analysis_start),
        "analysis_end": _optional_utc_z(result.analysis_end),
        "assumptions": _assumptions_payload(result.assumptions),
        "trades": [
            _configurable_trade_payload(
                trade,
                include_end_state=result.engine_version == CONFIGURABLE_ENGINE_VERSION,
            )
            for trade in result.trades
        ],
        "equity_series": [_equity_point_payload(point) for point in result.equity_series],
        "summary": _summary_payload(
            result.summary,
            include_end_state=result.engine_version == CONFIGURABLE_ENGINE_VERSION,
        ),
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _strategy_fingerprint(snapshot: Mapping[str, object]) -> str:
    serialized = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _failure_result(
    input: ConfigurableSimulationInput,
    status: str,
    reason: str,
) -> HistoricalSimulationResult:
    dataset_fingerprint = None
    preset_code = None
    preset_version = None
    analysis_start = None
    analysis_end = None
    if isinstance(input, ConfigurableSimulationInput):
        dataset_fingerprint = (
            input.dataset.manifest_fingerprint
            if isinstance(input.dataset, HistoricalDatasetManifest)
            else None
        )
        preset_code = input.preset.code if isinstance(input.preset, HistoricalPresetSnapshot) else None
        preset_version = input.preset.version if isinstance(input.preset, HistoricalPresetSnapshot) else None
        analysis_start = _safe_datetime(input.analysis_start)
        analysis_end = _safe_datetime(input.analysis_end)
    return HistoricalSimulationResult(
        status=status,
        failure_reason=reason,
        dataset_fingerprint=dataset_fingerprint,
        preset_code=preset_code,
        preset_version=preset_version,
        calculation_version=(input.calculation_version if isinstance(input, ConfigurableSimulationInput) else None),
        engine_version=(input.engine_version if isinstance(input, ConfigurableSimulationInput) else None),
        assumption_version=(input.assumption_version if isinstance(input, ConfigurableSimulationInput) else None),
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        assumptions=None,
        trades=(),
        equity_series=(),
        summary=None,
        safety_disclosures=SAFETY_DISCLOSURES,
        result_fingerprint=None,
        strategy_version=(input.strategy_version if isinstance(input, ConfigurableSimulationInput) else None),
        strategy_fingerprint=(input.strategy_fingerprint if isinstance(input, ConfigurableSimulationInput) else None),
        strategy_snapshot=(
            dict(input.strategy_snapshot)
            if isinstance(input, ConfigurableSimulationInput)
            and isinstance(input.strategy_snapshot, Mapping)
            else None
        ),
    )


def _strict_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or isinstance(value, float) or value is None:
        return None
    if isinstance(value, Decimal):
        decimal = value
    elif isinstance(value, str):
        try:
            decimal = Decimal(value)
        except (TypeError, ValueError):
            return None
    else:
        return None
    return decimal if decimal.is_finite() else None


def _multiply(left: Decimal, right: Decimal) -> Decimal:
    return left * right


def _divide(left: Decimal, right: Decimal) -> Decimal:
    return left / right


def _add(left: Decimal, right: Decimal) -> Decimal:
    return left + right


def _subtract(left: Decimal, right: Decimal) -> Decimal:
    return left - right


def _optional_utc_z(value: datetime | None) -> str | None:
    return None if value is None else _utc_z(value)


def _safe_datetime(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    try:
        return _normalize_utc_datetime(value)
    except (TypeError, ValueError):
        return None
