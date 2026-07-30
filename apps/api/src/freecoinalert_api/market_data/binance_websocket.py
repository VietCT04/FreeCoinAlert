import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID

from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.market_data.events import ClosedOneMinuteCandleEvent, PriceEvent


class BinanceWebSocketEventError(Exception):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def build_combined_stream_url(base_url: str, markets: dict[str, SupportedMarket]) -> str:
    streams = "/".join(
        stream
        for market in markets.values()
        for stream in (
            f"{market.stream_symbol.lower()}@aggTrade",
            f"{market.stream_symbol.lower()}@kline_1m",
        )
    )
    return f"{base_url}/stream?streams={streams}"


def parse_aggregate_trade(
    raw_message: str | bytes,
    *,
    markets: dict[str, SupportedMarket],
    received_at: datetime,
    connection_generation: UUID,
    observed_after_reconnect: bool,
    max_age_seconds: int,
    future_tolerance_seconds: int,
) -> PriceEvent:
    try:
        payload = json.loads(raw_message)
    except (TypeError, json.JSONDecodeError) as error:
        raise BinanceWebSocketEventError("invalid_json") from error

    if not isinstance(payload, dict):
        raise BinanceWebSocketEventError("invalid_wrapper")

    stream_name = payload.get("stream")
    data = payload.get("data")
    if not isinstance(stream_name, str) or not isinstance(data, dict):
        raise BinanceWebSocketEventError("invalid_wrapper")

    symbol = data.get("s")
    event_type = data.get("e")
    if not isinstance(symbol, str) or event_type != "aggTrade":
        raise BinanceWebSocketEventError("invalid_event")

    market = markets.get(symbol)
    if market is None or stream_name != f"{market.stream_symbol.lower()}@aggTrade":
        raise BinanceWebSocketEventError("unsupported_symbol")

    aggregate_id = require_nonnegative_int(data.get("a"), "invalid_aggregate_id")
    first_trade_id = require_nonnegative_int(data.get("f"), "invalid_first_trade_id")
    last_trade_id = require_nonnegative_int(data.get("l"), "invalid_last_trade_id")
    if first_trade_id > last_trade_id:
        raise BinanceWebSocketEventError("invalid_trade_range")

    price = require_price(data.get("p"))
    event_time = timestamp_from_milliseconds(data.get("E"))
    trade_time = timestamp_from_milliseconds(data.get("T"))
    age_seconds = (received_at - event_time).total_seconds()
    future_seconds = (trade_time - received_at).total_seconds()
    if age_seconds > max_age_seconds:
        raise BinanceWebSocketEventError("stale_event")
    if future_seconds > future_tolerance_seconds:
        raise BinanceWebSocketEventError("future_event")

    return PriceEvent(
        exchange="binance",
        market_type="spot",
        supported_market_id=market.id,
        symbol=symbol,
        provider_event_type="aggTrade",
        provider_event_id=aggregate_id,
        first_trade_id=first_trade_id,
        last_trade_id=last_trade_id,
        price=price,
        provider_event_time=event_time,
        provider_trade_time=trade_time,
        received_at=received_at,
        connection_generation=connection_generation,
        observed_after_reconnect=observed_after_reconnect,
    )


def require_nonnegative_int(value: object, category: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BinanceWebSocketEventError(category)
    return value


def require_price(value: object) -> Decimal:
    if not isinstance(value, str) or value.strip() != value or value == "":
        raise BinanceWebSocketEventError("invalid_price")
    try:
        price = Decimal(value)
    except InvalidOperation as error:
        raise BinanceWebSocketEventError("invalid_price") from error
    if not price.is_finite() or price <= 0:
        raise BinanceWebSocketEventError("invalid_price")
    return price


def timestamp_from_milliseconds(value: object) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BinanceWebSocketEventError("invalid_timestamp")
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def parse_closed_one_minute_candle(
    raw_message: str | bytes,
    *,
    markets: dict[str, SupportedMarket],
    received_at: datetime,
    connection_generation: UUID,
    max_age_seconds: int,
    future_tolerance_seconds: int,
) -> ClosedOneMinuteCandleEvent | None:
    try:
        payload = json.loads(raw_message)
    except (TypeError, json.JSONDecodeError) as error:
        raise BinanceWebSocketEventError("invalid_json") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise BinanceWebSocketEventError("invalid_wrapper")
    stream_name = payload.get("stream")
    data = payload["data"]
    candle = data.get("k")
    if not isinstance(stream_name, str) or data.get("e") != "kline" or not isinstance(candle, dict):
        raise BinanceWebSocketEventError("invalid_candle_event")
    symbol = data.get("s")
    market = markets.get(symbol) if isinstance(symbol, str) else None
    if market is None or stream_name != f"{market.stream_symbol.lower()}@kline_1m":
        raise BinanceWebSocketEventError("unsupported_symbol")
    if candle.get("s") != symbol or candle.get("i") != "1m":
        raise BinanceWebSocketEventError("invalid_candle_identity")
    if candle.get("x") is False:
        return None
    if candle.get("x") is not True:
        raise BinanceWebSocketEventError("invalid_candle_closed_flag")
    open_time = timestamp_from_milliseconds(candle.get("t"))
    close_time = timestamp_from_milliseconds(candle.get("T")) + timedelta(milliseconds=1)
    provider_close_time = timestamp_from_milliseconds(candle.get("T"))
    event_time = timestamp_from_milliseconds(data.get("E"))
    if open_time.second or open_time.microsecond or close_time != open_time + timedelta(minutes=1):
        raise BinanceWebSocketEventError("invalid_candle_boundary")
    if (received_at - event_time).total_seconds() > max_age_seconds:
        raise BinanceWebSocketEventError("stale_candle")
    if (event_time - received_at).total_seconds() > future_tolerance_seconds:
        raise BinanceWebSocketEventError("future_candle")
    open_price = require_price(candle.get("o"))
    high_price = require_price(candle.get("h"))
    low_price = require_price(candle.get("l"))
    close_price = require_price(candle.get("c"))
    if high_price < max(open_price, close_price) or low_price > min(open_price, close_price):
        raise BinanceWebSocketEventError("impossible_ohlc")
    return ClosedOneMinuteCandleEvent(
        exchange="binance", market_type="spot", supported_market_id=market.id, symbol=symbol,
        timeframe="1m", open_time=open_time, close_time=close_time,
        provider_close_time=provider_close_time, open_price=open_price, high_price=high_price,
        low_price=low_price, close_price=close_price, base_volume=require_nonnegative_decimal(candle.get("v")),
        quote_volume=require_nonnegative_decimal(candle.get("q")),
        trade_count=require_nonnegative_int(candle.get("n"), "invalid_trade_count"),
        first_trade_id=require_nonnegative_int(candle.get("f"), "invalid_first_trade_id"),
        last_trade_id=require_nonnegative_int(candle.get("L"), "invalid_last_trade_id"),
        provider_event_time=event_time, received_at=received_at, connection_generation=connection_generation,
    )


def require_nonnegative_decimal(value: object) -> Decimal:
    if not isinstance(value, str) or value.strip() != value or value == "":
        raise BinanceWebSocketEventError("invalid_volume")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise BinanceWebSocketEventError("invalid_volume") from error
    if not result.is_finite() or result < 0:
        raise BinanceWebSocketEventError("invalid_volume")
    return result
