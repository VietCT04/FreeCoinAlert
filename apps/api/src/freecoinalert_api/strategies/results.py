"""Immutable result and incremental-state contracts for strategy calculations."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


CalculationStatus = Literal[
    "success",
    "insufficient_history",
    "invalid_input",
    "gap_detected",
    "unsupported_version",
]


@dataclass(frozen=True, slots=True)
class SmaPoint:
    candle_id: UUID
    candle_revision: int
    candle_open_time: datetime
    candle_close_time: datetime
    period: Literal[200]
    value: Decimal


@dataclass(frozen=True, slots=True)
class SmaState:
    version: Literal["sma_close_v1"]
    period: Literal[200]
    supported_market_id: UUID
    timeframe: Literal["1h", "4h"]
    closes: tuple[Decimal, ...]
    rolling_sum: Decimal
    last_candle_id: UUID
    last_candle_revision: int
    last_open_time: datetime


@dataclass(frozen=True, slots=True)
class SmaSeriesResult:
    status: CalculationStatus
    points: tuple[SmaPoint, ...]


@dataclass(frozen=True, slots=True)
class SmaStateResult:
    status: CalculationStatus
    state: SmaState | None
    point: SmaPoint | None


@dataclass(frozen=True, slots=True)
class RsiPoint:
    candle_id: UUID
    candle_revision: int
    candle_open_time: datetime
    candle_close_time: datetime
    period: Literal[14]
    value: Decimal
    average_gain: Decimal
    average_loss: Decimal


@dataclass(frozen=True, slots=True)
class RsiState:
    version: Literal["rsi_wilder_close_v1"]
    period: Literal[14]
    supported_market_id: UUID
    timeframe: Literal["1h", "4h"]
    average_gain: Decimal
    average_loss: Decimal
    last_close: Decimal
    processed_change_count: int
    last_candle_id: UUID
    last_candle_revision: int
    last_open_time: datetime


@dataclass(frozen=True, slots=True)
class RsiSeriesResult:
    status: CalculationStatus
    points: tuple[RsiPoint, ...]


@dataclass(frozen=True, slots=True)
class RsiStateResult:
    status: CalculationStatus
    state: RsiState | None
    point: RsiPoint | None
