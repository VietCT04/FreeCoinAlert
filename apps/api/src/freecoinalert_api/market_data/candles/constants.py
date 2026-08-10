"""Product-owned candle coverage and retention invariants."""

from math import ceil

from freecoinalert_api.strategies.rsi import RSI_PERIOD
from freecoinalert_api.strategies.sma import SMA_PERIOD


HISTORICAL_ANALYSIS_MAX_RANGE_DAYS = 730
CANDLE_OPERATIONAL_BUFFER_DAYS = 1
MIN_CANDLE_BOOTSTRAP_DAYS = 35
MAX_CANDLE_BOOTSTRAP_DAYS = 765
SUPPORTED_CANDLE_TIMEFRAME_HOURS = {"1m": 1 / 60, "1h": 1, "4h": 4}

# RSI needs one more candle than its period to establish the first value.
REQUIRED_PRESET_WARMUP_CANDLES = {
    "price_sma_cross": SMA_PERIOD,
    "rsi_threshold_cross": RSI_PERIOD + 1,
}
MAX_REQUIRED_WARMUP_CANDLES = max(REQUIRED_PRESET_WARMUP_CANDLES.values())
MAX_SUPPORTED_ENTRY_TIMEFRAME_HOURS = max(
    SUPPORTED_CANDLE_TIMEFRAME_HOURS.values()
)
CANDLE_REQUIRED_RETENTION_DAYS = (
    HISTORICAL_ANALYSIS_MAX_RANGE_DAYS
    + ceil(MAX_REQUIRED_WARMUP_CANDLES * MAX_SUPPORTED_ENTRY_TIMEFRAME_HOURS / 24)
    + CANDLE_OPERATIONAL_BUFFER_DAYS
)

if CANDLE_REQUIRED_RETENTION_DAYS != 765:  # pragma: no cover - invariant guard
    raise RuntimeError("The candle retention invariant must remain 765 days.")


def validate_candle_retention_days(retention_days: int) -> int:
    if retention_days < CANDLE_REQUIRED_RETENTION_DAYS:
        raise ValueError(
            "Candle retention cannot be lower than the historical-analysis product invariant."
        )
    return retention_days
