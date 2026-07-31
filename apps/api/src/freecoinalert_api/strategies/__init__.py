"""Pure, versioned indicator calculations for confirmed market candles."""

from freecoinalert_api.strategies.candles import StrategyCandle
from freecoinalert_api.strategies.keys import StrategyCalculationKey
from freecoinalert_api.strategies.rsi import (
    advance_rsi_state,
    calculate_rsi_series,
    initialize_rsi_state,
)
from freecoinalert_api.strategies.sma import (
    advance_sma_state,
    calculate_sma_series,
    initialize_sma_state,
)

__all__ = [
    "StrategyCalculationKey",
    "StrategyCandle",
    "advance_rsi_state",
    "advance_sma_state",
    "calculate_rsi_series",
    "calculate_sma_series",
    "initialize_rsi_state",
    "initialize_sma_state",
]
