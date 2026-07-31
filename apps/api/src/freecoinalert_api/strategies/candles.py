"""Provider-neutral confirmed-candle inputs and series validation."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from freecoinalert_api.strategies.results import CalculationStatus


Timeframe = Literal["1h", "4h"]
_TIMEFRAME_DURATIONS: dict[Timeframe, timedelta] = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}


@dataclass(frozen=True, slots=True)
class StrategyCandle:
    candle_id: UUID
    candle_revision: int
    supported_market_id: UUID
    timeframe: Timeframe
    open_time: datetime
    close_time: datetime
    close_price: Decimal
    status: Literal["complete"]


def validate_candle_series(
    candles: tuple[StrategyCandle, ...],
    required_candle_count: int,
) -> CalculationStatus:
    if not candles:
        return "insufficient_history"

    first_candle = candles[0]
    if not _is_valid_candle(first_candle):
        return "invalid_input"

    previous_candle = first_candle
    candle_ids = {first_candle.candle_id}
    open_times = {first_candle.open_time}

    for candle in candles[1:]:
        if not _is_valid_candle(candle):
            return "invalid_input"
        if candle.supported_market_id != first_candle.supported_market_id:
            return "invalid_input"
        if candle.timeframe != first_candle.timeframe:
            return "invalid_input"
        if candle.candle_id in candle_ids or candle.open_time in open_times:
            return "invalid_input"
        if candle.open_time <= previous_candle.open_time:
            return "invalid_input"
        if candle.open_time != previous_candle.close_time:
            return "gap_detected"
        candle_ids.add(candle.candle_id)
        open_times.add(candle.open_time)
        previous_candle = candle

    if len(candles) < required_candle_count:
        return "insufficient_history"
    return "success"


def validate_next_candle(
    state_market_id: UUID,
    state_timeframe: Timeframe,
    state_last_open_time: datetime,
    candle: StrategyCandle,
) -> CalculationStatus:
    if not _is_valid_candle(candle):
        return "invalid_input"
    if candle.supported_market_id != state_market_id:
        return "invalid_input"
    if candle.timeframe != state_timeframe:
        return "invalid_input"
    expected_open_time = state_last_open_time + _TIMEFRAME_DURATIONS[state_timeframe]
    if candle.open_time != expected_open_time:
        return "gap_detected"
    return "success"


def _is_valid_candle(candle: StrategyCandle) -> bool:
    if candle.candle_revision < 1 or candle.status != "complete":
        return False
    if candle.timeframe not in _TIMEFRAME_DURATIONS:
        return False
    if not _is_utc(candle.open_time) or not _is_utc(candle.close_time):
        return False
    if candle.close_time != candle.open_time + _TIMEFRAME_DURATIONS[candle.timeframe]:
        return False
    return candle.close_price.is_finite() and candle.close_price > Decimal("0")


def _is_utc(value: datetime) -> bool:
    return value.tzinfo == UTC
