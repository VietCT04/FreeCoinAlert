from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.models.signal_preset import SignalPreset
from freecoinalert_api.db.repositories.market_candles import list_complete_candles
from freecoinalert_api.strategies import StrategyCandle, calculate_rsi_series, calculate_sma_series
from freecoinalert_api.strategies.keys import StrategyCalculationKey
from freecoinalert_api.strategies.rsi import RSI_CALCULATION_VERSION
from freecoinalert_api.strategies.sma import SMA_CALCULATION_VERSION


@dataclass(frozen=True, slots=True)
class PresetCalculation:
    status: str
    key: StrategyCalculationKey
    left_value: Decimal | None
    right_value: Decimal | None
    calculation_state: dict[str, str | int] | None


def calculation_key(preset: SignalPreset, supported_market_id: UUID) -> StrategyCalculationKey:
    if preset.strategy_type == "price_sma_cross":
        return StrategyCalculationKey(
            supported_market_id=supported_market_id,
            timeframe=preset.timeframe,  # type: ignore[arg-type]
            strategy_type="price_sma_cross",
            calculation_version=SMA_CALCULATION_VERSION,
            period=200,
            price_input="close",
        )
    return StrategyCalculationKey(
        supported_market_id=supported_market_id,
        timeframe=preset.timeframe,  # type: ignore[arg-type]
        strategy_type="rsi_threshold_cross",
        calculation_version=RSI_CALCULATION_VERSION,
        period=14,
        price_input="close",
    )


async def calculate_preset(
    session: AsyncSession,
    *,
    preset: SignalPreset,
    candle: MarketCandle,
    cache: dict[tuple[StrategyCalculationKey, UUID, int], PresetCalculation],
) -> PresetCalculation:
    key = calculation_key(preset, candle.supported_market_id)
    cache_key = (key, candle.id, candle.revision)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    required = 200 if preset.strategy_type == "price_sma_cross" else 15
    candles = await list_complete_candles(
        session,
        supported_market_id=candle.supported_market_id,
        timeframe=candle.timeframe,
        start_open_time=datetime(1970, 1, 1, tzinfo=UTC),
        end_open_time=candle.close_time.astimezone(UTC),
        limit=required,
    )
    strategy_candles = tuple(_strategy_candle(item) for item in reversed(candles))
    result = _calculate(key, strategy_candles, candle, preset)
    cache[cache_key] = result
    return result


def _calculate(
    key: StrategyCalculationKey,
    candles: tuple[StrategyCandle, ...],
    candle: MarketCandle,
    preset: SignalPreset,
) -> PresetCalculation:
    if preset.strategy_type == "price_sma_cross":
        series = calculate_sma_series(candles)
        if series.status != "success":
            return PresetCalculation(series.status, key, None, None, None)
        point = series.points[-1]
        return PresetCalculation(
            "success",
            key,
            candle.close_price,
            point.value,
            {
                "schemaVersion": 1,
                "calculationVersion": SMA_CALCULATION_VERSION,
                "lastSma": str(point.value),
            },
        )

    series = calculate_rsi_series(candles)
    if series.status != "success":
        return PresetCalculation(series.status, key, None, None, None)
    point = series.points[-1]
    return PresetCalculation(
        "success",
        key,
        point.value,
        preset.threshold,
        {
            "schemaVersion": 1,
            "calculationVersion": RSI_CALCULATION_VERSION,
            "averageGain": str(point.average_gain),
            "averageLoss": str(point.average_loss),
            "lastClose": str(candle.close_price),
            "processedChangeCount": len(candles) - 1,
        },
    )


def _strategy_candle(candle: MarketCandle) -> StrategyCandle:
    if candle.close_price is None:
        raise ValueError("Complete candles require a close price.")
    return StrategyCandle(
        candle_id=candle.id,
        candle_revision=candle.revision,
        supported_market_id=candle.supported_market_id,
        timeframe=candle.timeframe,  # type: ignore[arg-type]
        open_time=candle.open_time.astimezone(UTC),
        close_time=candle.close_time.astimezone(UTC),
        close_price=candle.close_price,
        status="complete",
    )
