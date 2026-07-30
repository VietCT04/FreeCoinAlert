from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PriceEvent:
    exchange: Literal["binance"]
    market_type: Literal["spot"]
    supported_market_id: UUID
    symbol: str
    provider_event_type: Literal["aggTrade"]
    provider_event_id: int
    first_trade_id: int
    last_trade_id: int
    price: Decimal
    provider_event_time: datetime
    provider_trade_time: datetime
    received_at: datetime
    connection_generation: UUID
    observed_after_reconnect: bool


@dataclass(frozen=True, slots=True)
class ClosedOneMinuteCandleEvent:
    exchange: Literal["binance"]
    market_type: Literal["spot"]
    supported_market_id: UUID
    symbol: str
    timeframe: Literal["1m"]
    open_time: datetime
    close_time: datetime
    provider_close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    base_volume: Decimal
    quote_volume: Decimal
    trade_count: int
    first_trade_id: int
    last_trade_id: int
    provider_event_time: datetime
    received_at: datetime
    connection_generation: UUID


@dataclass(frozen=True, slots=True)
class ConfirmedCandleEvent:
    candle_id: UUID
    candle_revision: int
    supported_market_id: UUID
    exchange: Literal["binance"]
    market_type: Literal["spot"]
    symbol: str
    timeframe: Literal["1m", "1h", "4h"]
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    base_volume: Decimal
    quote_volume: Decimal
    trade_count: int
    source_kind: Literal["binance_kline", "aggregate_1m"]
    observed_at: datetime
    corrected: bool
