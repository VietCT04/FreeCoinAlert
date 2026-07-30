from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from freecoinalert_api.schemas.auth import to_camel_case


class MarketPriceRulesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    minimum: str = Field(serialization_alias="min")
    maximum: str = Field(serialization_alias="max")
    tick: str


class MarketResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    exchange: Literal["binance"]
    market_type: Literal["spot"]
    symbol: str
    base_asset: str | None
    quote_asset: str | None
    status: Literal["available", "unavailable"]
    price_rules: MarketPriceRulesResponse | None
    metadata_checked_at: datetime | None


class MarketEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    markets: list[MarketResponse]
