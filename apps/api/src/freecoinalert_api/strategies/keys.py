"""Immutable keys for sharing strategy calculations across subscriptions."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StrategyCalculationKey:
    supported_market_id: UUID
    timeframe: Literal["1h", "4h"]
    strategy_type: Literal["price_sma_cross", "rsi_threshold_cross"]
    calculation_version: Literal["sma_close_v1", "rsi_wilder_close_v1"]
    period: Literal[14, 200]
    price_input: Literal["close"]
