"""Immutable strategy contracts for historical-analysis runs.

This module owns request normalization and the canonical representation used by
run idempotency and persisted strategy snapshots. It deliberately does not
execute a strategy; the simulation engine is owned by the following issue.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, TypeAlias


STRATEGY_SNAPSHOT_SCHEMA_VERSION = "historical_strategy_snapshot_v1"
LEGACY_STRATEGY_VERSION = "legacy_fixed_horizon_v1"
CONFIGURABLE_STRATEGY_VERSION = "configurable_exit_v1"
CONFIGURABLE_SIMULATION_VERSION = "historical_configurable_exit_v1"
CONFIGURABLE_ASSUMPTION_VERSION = "configurable_exit_v1"
LEGACY_HOLDING_CANDLES = 6
MAX_EXIT_RULES = 4
MAX_HOLDING_CANDLES = 2_200
MAX_DECIMAL_PLACES = 18

PositionDirection = Literal["long", "synthetic_short"]
SignalDirection = Literal["cross_above", "cross_below"]
RsiDirection = Literal["cross_above", "cross_below"]


@dataclass(frozen=True, slots=True)
class StrategyValidationIssue:
    field: str
    code: str

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "code": self.code}


class StrategyValidationError(ValueError):
    """Safe, field-level validation failure for a submitted strategy."""

    def __init__(self, issues: tuple[StrategyValidationIssue, ...]) -> None:
        self.issues = issues
        super().__init__("The historical-analysis strategy is invalid.")


@dataclass(frozen=True, slots=True)
class TakeProfitPercentRule:
    percent: Decimal

    @property
    def rule_type(self) -> Literal["take_profit_percent"]:
        return "take_profit_percent"

    def to_snapshot(self) -> dict[str, object]:
        return {"type": self.rule_type, "percent": _decimal_string(self.percent)}


@dataclass(frozen=True, slots=True)
class StopLossPercentRule:
    percent: Decimal

    @property
    def rule_type(self) -> Literal["stop_loss_percent"]:
        return "stop_loss_percent"

    def to_snapshot(self) -> dict[str, object]:
        return {"type": self.rule_type, "percent": _decimal_string(self.percent)}


@dataclass(frozen=True, slots=True)
class RsiThresholdCrossRule:
    direction: RsiDirection
    threshold: Decimal
    timeframe: str
    calculation_version: str = "rsi_wilder_close_v1"
    period: int = 14
    price_input: Literal["close"] = "close"

    @property
    def rule_type(self) -> Literal["rsi_threshold_cross"]:
        return "rsi_threshold_cross"

    def to_snapshot(self) -> dict[str, object]:
        return {
            "type": self.rule_type,
            "period": self.period,
            "direction": self.direction,
            "threshold": _decimal_string(self.threshold),
            "price_input": self.price_input,
            "timeframe": self.timeframe,
            "calculation_version": self.calculation_version,
        }


@dataclass(frozen=True, slots=True)
class MaxHoldingCandlesRule:
    candles: int

    @property
    def rule_type(self) -> Literal["max_holding_candles"]:
        return "max_holding_candles"

    def to_snapshot(self) -> dict[str, object]:
        return {"type": self.rule_type, "candles": self.candles}


ExitRule: TypeAlias = (
    TakeProfitPercentRule
    | StopLossPercentRule
    | RsiThresholdCrossRule
    | MaxHoldingCandlesRule
)


@dataclass(frozen=True, slots=True)
class StrategySnapshot:
    version: str
    entry_preset_code: str
    entry_preset_version: int
    entry_timeframe: str
    entry_signal_direction: SignalDirection
    entry_calculation_version: str
    position_direction: PositionDirection
    exit_rules: tuple[ExitRule, ...]

    def to_snapshot(self) -> dict[str, object]:
        return {
            "schema_version": STRATEGY_SNAPSHOT_SCHEMA_VERSION,
            "version": self.version,
            "entry": {
                "preset_code": self.entry_preset_code,
                "preset_version": self.entry_preset_version,
                "timeframe": self.entry_timeframe,
                "signal_direction": self.entry_signal_direction,
                "calculation_version": self.entry_calculation_version,
            },
            "position_direction": self.position_direction,
            "exit_rules": [rule.to_snapshot() for rule in self.exit_rules],
        }

    @property
    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.to_snapshot(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def legacy_strategy_snapshot(
    *,
    preset_code: str,
    preset_version: int,
    timeframe: str,
    signal_direction: SignalDirection,
    calculation_version: str,
) -> StrategySnapshot:
    position_direction: PositionDirection = (
        "long" if signal_direction == "cross_above" else "synthetic_short"
    )
    return StrategySnapshot(
        version=LEGACY_STRATEGY_VERSION,
        entry_preset_code=preset_code,
        entry_preset_version=preset_version,
        entry_timeframe=timeframe,
        entry_signal_direction=signal_direction,
        entry_calculation_version=calculation_version,
        position_direction=position_direction,
        exit_rules=(MaxHoldingCandlesRule(candles=LEGACY_HOLDING_CANDLES),),
    )


def normalize_strategy(
    payload: Mapping[str, object] | None,
    *,
    preset_code: str,
    preset_version: int,
    timeframe: str,
    signal_direction: SignalDirection,
    calculation_version: str,
) -> StrategySnapshot:
    if payload is None:
        return legacy_strategy_snapshot(
            preset_code=preset_code,
            preset_version=preset_version,
            timeframe=timeframe,
            signal_direction=signal_direction,
            calculation_version=calculation_version,
        )

    issues: list[StrategyValidationIssue] = []
    position_direction = payload.get("position_direction")
    if position_direction != "long":
        issues.append(
            StrategyValidationIssue("strategy.positionDirection", "UNSUPPORTED_DIRECTION")
        )

    raw_rules = payload.get("exit_rules")
    if not isinstance(raw_rules, list):
        raise StrategyValidationError(
            (StrategyValidationIssue("strategy.exitRules", "REQUIRED"),)
        )
    if len(raw_rules) > MAX_EXIT_RULES:
        issues.append(
            StrategyValidationIssue("strategy.exitRules", "TOO_MANY_RULES")
        )

    rules: list[ExitRule] = []
    seen_types: set[str] = set()
    for index, raw_rule in enumerate(raw_rules):
        field = f"strategy.exitRules[{index}]"
        if not isinstance(raw_rule, Mapping):
            issues.append(StrategyValidationIssue(field, "MALFORMED_RULE"))
            continue
        rule_type = raw_rule.get("type")
        if not isinstance(rule_type, str):
            issues.append(StrategyValidationIssue(f"{field}.type", "REQUIRED"))
            continue
        if rule_type in seen_types:
            issues.append(StrategyValidationIssue(f"{field}.type", "DUPLICATE_RULE"))
            continue
        seen_types.add(rule_type)

        if rule_type == "take_profit_percent":
            _append_rule(
                rules,
                _take_profit_rule(raw_rule, field, issues),
            )
        elif rule_type == "stop_loss_percent":
            _append_rule(
                rules,
                _stop_loss_rule(raw_rule, field, issues),
            )
        elif rule_type == "rsi_threshold_cross":
            _append_rule(
                rules,
                _rsi_rule(raw_rule, field, timeframe, issues),
            )
        elif rule_type == "max_holding_candles":
            _append_rule(
                rules,
                _max_holding_rule(raw_rule, field, issues),
            )
        else:
            issues.append(
                StrategyValidationIssue(f"{field}.type", "UNSUPPORTED_RULE_TYPE")
            )

    if "max_holding_candles" not in seen_types:
        issues.append(
            StrategyValidationIssue("strategy.exitRules", "REQUIRED_MAX_HOLDING_RULE")
        )
    if issues:
        raise StrategyValidationError(tuple(issues))

    canonical_rules = tuple(
        sorted(rules, key=lambda rule: _RULE_ORDER[rule.rule_type])
    )
    return StrategySnapshot(
        version=CONFIGURABLE_STRATEGY_VERSION,
        entry_preset_code=preset_code,
        entry_preset_version=preset_version,
        entry_timeframe=timeframe,
        entry_signal_direction=signal_direction,
        entry_calculation_version=calculation_version,
        position_direction="long",
        exit_rules=canonical_rules,
    )


def capabilities_payload(*, configurable_available: bool) -> dict[str, object]:
    return {
        "configurable_strategy_available": configurable_available,
        "position_directions": ["long"],
        "maximum_exit_rules": MAX_EXIT_RULES,
        "required_exit_rule_types": ["max_holding_candles"],
        "supported_exit_rule_types": [
            "take_profit_percent",
            "stop_loss_percent",
            "rsi_threshold_cross",
            "max_holding_candles",
        ],
        "same_candle_priority": [
            "stop_loss_percent",
            "take_profit_percent",
            "rsi_threshold_cross",
            "max_holding_candles",
        ],
        "max_holding_candles": {
            "minimum": 1,
            "maximum": MAX_HOLDING_CANDLES,
            "default": LEGACY_HOLDING_CANDLES,
        },
        "exit_rule_limits": {
            "take_profit_percent": {
                "minimum": "0.01",
                "maximum": "1000",
                "maximumInclusive": True,
            },
            "stop_loss_percent": {
                "minimum": "0.01",
                "maximum": "100",
                "maximumInclusive": False,
            },
            "rsi_threshold_cross": {
                "minimum": "0",
                "minimumInclusive": False,
                "maximum": "100",
                "maximumInclusive": False,
                "directions": ["cross_above", "cross_below"],
                "period": 14,
                "priceInput": "close",
                "calculationVersion": "rsi_wilder_close_v1",
            },
        },
    }


_RULE_ORDER = {
    "stop_loss_percent": 0,
    "take_profit_percent": 1,
    "rsi_threshold_cross": 2,
    "max_holding_candles": 3,
}


def _append_rule(rules: list[ExitRule], rule: ExitRule | None) -> None:
    if rule is not None:
        rules.append(rule)


def _take_profit_rule(
    raw_rule: Mapping[str, object],
    field: str,
    issues: list[StrategyValidationIssue],
) -> TakeProfitPercentRule | None:
    _check_fields(raw_rule, field, {"type", "percent"}, issues)
    percent = _parse_decimal(raw_rule.get("percent"), f"{field}.percent", issues)
    if percent is None:
        return None
    if percent < Decimal("0.01") or percent > Decimal("1000"):
        issues.append(StrategyValidationIssue(f"{field}.percent", "OUT_OF_RANGE"))
        return None
    return TakeProfitPercentRule(percent=percent)


def _stop_loss_rule(
    raw_rule: Mapping[str, object],
    field: str,
    issues: list[StrategyValidationIssue],
) -> StopLossPercentRule | None:
    _check_fields(raw_rule, field, {"type", "percent"}, issues)
    percent = _parse_decimal(raw_rule.get("percent"), f"{field}.percent", issues)
    if percent is None:
        return None
    if percent < Decimal("0.01") or percent >= Decimal("100"):
        issues.append(StrategyValidationIssue(f"{field}.percent", "OUT_OF_RANGE"))
        return None
    return StopLossPercentRule(percent=percent)


def _rsi_rule(
    raw_rule: Mapping[str, object],
    field: str,
    timeframe: str,
    issues: list[StrategyValidationIssue],
) -> RsiThresholdCrossRule | None:
    _check_fields(raw_rule, field, {"type", "direction", "threshold"}, issues)
    direction = raw_rule.get("direction")
    if direction not in {"cross_above", "cross_below"}:
        issues.append(StrategyValidationIssue(f"{field}.direction", "UNSUPPORTED_DIRECTION"))
        return None
    threshold = _parse_decimal(raw_rule.get("threshold"), f"{field}.threshold", issues)
    if threshold is None:
        return None
    if threshold <= Decimal("0") or threshold >= Decimal("100"):
        issues.append(StrategyValidationIssue(f"{field}.threshold", "OUT_OF_RANGE"))
        return None
    return RsiThresholdCrossRule(
        direction=direction,
        threshold=threshold,
        timeframe=timeframe,
    )


def _max_holding_rule(
    raw_rule: Mapping[str, object],
    field: str,
    issues: list[StrategyValidationIssue],
) -> MaxHoldingCandlesRule | None:
    _check_fields(raw_rule, field, {"type", "candles"}, issues)
    candles = raw_rule.get("candles")
    if not isinstance(candles, int) or isinstance(candles, bool):
        issues.append(StrategyValidationIssue(f"{field}.candles", "INVALID_TYPE"))
        return None
    if candles < 1 or candles > MAX_HOLDING_CANDLES:
        issues.append(StrategyValidationIssue(f"{field}.candles", "OUT_OF_RANGE"))
        return None
    return MaxHoldingCandlesRule(candles=candles)


def _check_fields(
    raw_rule: Mapping[str, object],
    field: str,
    allowed: set[str],
    issues: list[StrategyValidationIssue],
) -> None:
    for key in raw_rule:
        if not isinstance(key, str):
            issues.append(StrategyValidationIssue(f"{field}.unknown", "UNSUPPORTED_FIELD"))
        elif key not in allowed:
            issues.append(StrategyValidationIssue(f"{field}.{key}", "UNSUPPORTED_FIELD"))


def _parse_decimal(
    value: object,
    field: str,
    issues: list[StrategyValidationIssue],
) -> Decimal | None:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            issues.append(StrategyValidationIssue(field, "INVALID_DECIMAL"))
            return None
    else:
        issues.append(StrategyValidationIssue(field, "INVALID_TYPE"))
        return None
    if not parsed.is_finite():
        issues.append(StrategyValidationIssue(field, "INVALID_DECIMAL"))
        return None
    if max(0, -parsed.as_tuple().exponent) > MAX_DECIMAL_PLACES:
        issues.append(StrategyValidationIssue(field, "TOO_MANY_DECIMAL_PLACES"))
        return None
    return parsed


def _decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")
