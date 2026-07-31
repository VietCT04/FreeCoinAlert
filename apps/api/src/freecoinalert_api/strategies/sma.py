"""Version 1 close-price SMA 200 calculations."""

from decimal import Decimal

from freecoinalert_api.strategies.candles import (
    StrategyCandle,
    validate_candle_series,
    validate_next_candle,
)
from freecoinalert_api.strategies.decimal_math import calculate_price_average
from freecoinalert_api.strategies.results import (
    SmaPoint,
    SmaSeriesResult,
    SmaState,
    SmaStateResult,
)


SMA_PERIOD = 200
SMA_CALCULATION_VERSION = "sma_close_v1"


def calculate_sma_series(candles: tuple[StrategyCandle, ...]) -> SmaSeriesResult:
    status = validate_candle_series(candles, SMA_PERIOD)
    if status != "success":
        return SmaSeriesResult(status=status, points=())

    rolling_sum = sum((candle.close_price for candle in candles[:SMA_PERIOD]), Decimal("0"))
    points = [_point(candles[SMA_PERIOD - 1], rolling_sum)]
    for index in range(SMA_PERIOD, len(candles)):
        rolling_sum -= candles[index - SMA_PERIOD].close_price
        rolling_sum += candles[index].close_price
        points.append(_point(candles[index], rolling_sum))
    return SmaSeriesResult(status="success", points=tuple(points))


def initialize_sma_state(candles: tuple[StrategyCandle, ...]) -> SmaStateResult:
    series = calculate_sma_series(candles)
    if series.status != "success":
        return SmaStateResult(status=series.status, state=None, point=None)

    latest_candle = candles[-1]
    closes = tuple(candle.close_price for candle in candles[-SMA_PERIOD:])
    state = SmaState(
        version=SMA_CALCULATION_VERSION,
        period=SMA_PERIOD,
        supported_market_id=latest_candle.supported_market_id,
        timeframe=latest_candle.timeframe,
        closes=closes,
        rolling_sum=sum(closes, Decimal("0")),
        last_candle_id=latest_candle.candle_id,
        last_candle_revision=latest_candle.candle_revision,
        last_open_time=latest_candle.open_time,
    )
    return SmaStateResult(status="success", state=state, point=series.points[-1])


def advance_sma_state(state: SmaState, candle: StrategyCandle) -> SmaStateResult:
    if state.version != SMA_CALCULATION_VERSION or state.period != SMA_PERIOD:
        return SmaStateResult(status="unsupported_version", state=None, point=None)
    if len(state.closes) != SMA_PERIOD:
        return SmaStateResult(status="invalid_input", state=None, point=None)
    status = validate_next_candle(
        state.supported_market_id,
        state.timeframe,
        state.last_open_time,
        candle,
    )
    if status != "success":
        return SmaStateResult(status=status, state=None, point=None)

    closes = (*state.closes[1:], candle.close_price)
    rolling_sum = state.rolling_sum - state.closes[0] + candle.close_price
    next_state = SmaState(
        version=SMA_CALCULATION_VERSION,
        period=SMA_PERIOD,
        supported_market_id=state.supported_market_id,
        timeframe=state.timeframe,
        closes=closes,
        rolling_sum=rolling_sum,
        last_candle_id=candle.candle_id,
        last_candle_revision=candle.candle_revision,
        last_open_time=candle.open_time,
    )
    return SmaStateResult(
        status="success",
        state=next_state,
        point=_point(candle, rolling_sum),
    )


def _point(candle: StrategyCandle, rolling_sum: Decimal) -> SmaPoint:
    return SmaPoint(
        candle_id=candle.candle_id,
        candle_revision=candle.candle_revision,
        candle_open_time=candle.open_time,
        candle_close_time=candle.close_time,
        period=SMA_PERIOD,
        value=calculate_price_average(rolling_sum, SMA_PERIOD),
    )
