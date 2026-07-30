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
