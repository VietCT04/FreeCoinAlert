"""Version 1 Wilder close-price RSI 14 calculations."""

from decimal import Decimal, localcontext

from freecoinalert_api.strategies.candles import (
    StrategyCandle,
    validate_candle_series,
    validate_next_candle,
)
from freecoinalert_api.strategies.decimal_math import (
    CALCULATION_PRECISION,
    calculate_price_average,
    calculate_wilder_average,
    quantize_rsi,
)
from freecoinalert_api.strategies.errors import StrategyCalculationError
from freecoinalert_api.strategies.results import (
    RsiPoint,
    RsiSeriesResult,
    RsiState,
    RsiStateResult,
)


RSI_PERIOD = 14
RSI_CALCULATION_VERSION = "rsi_wilder_close_v1"


def calculate_rsi_series(candles: tuple[StrategyCandle, ...]) -> RsiSeriesResult:
    status = validate_candle_series(candles, RSI_PERIOD + 1)
    if status != "success":
        return RsiSeriesResult(status=status, points=())

    gains, losses = _changes(candles[: RSI_PERIOD + 1])
    average_gain = calculate_price_average(sum(gains, Decimal("0")), RSI_PERIOD)
    average_loss = calculate_price_average(sum(losses, Decimal("0")), RSI_PERIOD)
    points = [_point(candles[RSI_PERIOD], average_gain, average_loss)]
    for index in range(RSI_PERIOD + 1, len(candles)):
        candle = candles[index]
        gain, loss = _change(candles[index - 1].close_price, candle.close_price)
        average_gain = calculate_wilder_average(average_gain, gain, RSI_PERIOD)
        average_loss = calculate_wilder_average(average_loss, loss, RSI_PERIOD)
        points.append(_point(candle, average_gain, average_loss))
    return RsiSeriesResult(status="success", points=tuple(points))


def initialize_rsi_state(candles: tuple[StrategyCandle, ...]) -> RsiStateResult:
    series = calculate_rsi_series(candles)
    if series.status != "success":
        return RsiStateResult(status=series.status, state=None, point=None)

    latest_candle = candles[-1]
    latest_point = series.points[-1]
    state = RsiState(
        version=RSI_CALCULATION_VERSION,
        period=RSI_PERIOD,
        supported_market_id=latest_candle.supported_market_id,
        timeframe=latest_candle.timeframe,
        average_gain=latest_point.average_gain,
        average_loss=latest_point.average_loss,
        last_close=latest_candle.close_price,
        processed_change_count=len(candles) - 1,
        last_candle_id=latest_candle.candle_id,
        last_candle_revision=latest_candle.candle_revision,
        last_open_time=latest_candle.open_time,
    )
    return RsiStateResult(status="success", state=state, point=latest_point)


def advance_rsi_state(state: RsiState, candle: StrategyCandle) -> RsiStateResult:
    if state.version != RSI_CALCULATION_VERSION or state.period != RSI_PERIOD:
        return RsiStateResult(status="unsupported_version", state=None, point=None)
    if state.processed_change_count < RSI_PERIOD:
        return RsiStateResult(status="invalid_input", state=None, point=None)
    if not state.average_gain.is_finite() or state.average_gain < Decimal("0"):
        return RsiStateResult(status="invalid_input", state=None, point=None)
    if not state.average_loss.is_finite() or state.average_loss < Decimal("0"):
        return RsiStateResult(status="invalid_input", state=None, point=None)
    if not state.last_close.is_finite() or state.last_close <= Decimal("0"):
        return RsiStateResult(status="invalid_input", state=None, point=None)
    status = validate_next_candle(
        state.supported_market_id,
        state.timeframe,
        state.last_open_time,
        candle,
    )
    if status != "success":
        return RsiStateResult(status=status, state=None, point=None)

    gain, loss = _change(state.last_close, candle.close_price)
    average_gain = calculate_wilder_average(state.average_gain, gain, RSI_PERIOD)
    average_loss = calculate_wilder_average(state.average_loss, loss, RSI_PERIOD)
    point = _point(candle, average_gain, average_loss)
    next_state = RsiState(
        version=RSI_CALCULATION_VERSION,
        period=RSI_PERIOD,
        supported_market_id=state.supported_market_id,
        timeframe=state.timeframe,
        average_gain=average_gain,
        average_loss=average_loss,
        last_close=candle.close_price,
        processed_change_count=state.processed_change_count + 1,
        last_candle_id=candle.candle_id,
        last_candle_revision=candle.candle_revision,
        last_open_time=candle.open_time,
    )
    return RsiStateResult(status="success", state=next_state, point=point)


def _changes(candles: tuple[StrategyCandle, ...]) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for previous_candle, candle in zip(candles, candles[1:]):
        gain, loss = _change(previous_candle.close_price, candle.close_price)
        gains.append(gain)
        losses.append(loss)
    return tuple(gains), tuple(losses)


def _change(previous_close: Decimal, current_close: Decimal) -> tuple[Decimal, Decimal]:
    difference = current_close - previous_close
    return max(difference, Decimal("0")), max(-difference, Decimal("0"))


def _point(candle: StrategyCandle, average_gain: Decimal, average_loss: Decimal) -> RsiPoint:
    value = _calculate_rsi_value(average_gain, average_loss)
    return RsiPoint(
        candle_id=candle.candle_id,
        candle_revision=candle.candle_revision,
        candle_open_time=candle.open_time,
        candle_close_time=candle.close_time,
        period=RSI_PERIOD,
        value=value,
        average_gain=average_gain,
        average_loss=average_loss,
    )


def _calculate_rsi_value(average_gain: Decimal, average_loss: Decimal) -> Decimal:
    if average_gain == 0 and average_loss == 0:
        return Decimal("50.00000000")
    if average_loss == 0:
        return Decimal("100.00000000")
    if average_gain == 0:
        return Decimal("0.00000000")
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        relative_strength = average_gain / average_loss
        value = quantize_rsi(
            Decimal("100")
            - (Decimal("100") / (Decimal("1") + relative_strength))
        )
    if not Decimal("0") <= value <= Decimal("100"):
        raise StrategyCalculationError("RSI calculation produced a value outside its valid range.")
    return value
