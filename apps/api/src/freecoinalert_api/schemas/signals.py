import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr

from freecoinalert_api.schemas.auth import to_camel_case


class SignalSubscriptionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: StrictStr
    market_type: StrictStr
    symbol: StrictStr
    preset_code: StrictStr
    preset_version: StrictInt


class SignalParametersResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    period: int
    threshold: str | None
    price_input: Literal["close"]


class SignalPresetResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    code: str
    version: int
    name: str
    description: str
    strategy_type: Literal["price_sma_cross", "rsi_threshold_cross"]
    timeframe: Literal["1h", "4h"]
    direction: Literal["cross_above", "cross_below"]
    parameters: SignalParametersResponse
    status: Literal["available"]


class SignalPresetEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    presets: list[SignalPresetResponse]


class SignalSubscriptionMarketResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    exchange: Literal["binance"]
    market_type: Literal["spot"]
    symbol: str
    base_asset: str
    quote_asset: str


class SignalSubscriptionPresetResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    code: str
    version: int
    name: str
    timeframe: Literal["1h", "4h"]
    direction: Literal["cross_above", "cross_below"]
    parameters: SignalParametersResponse


class SignalSubscriptionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    id: uuid.UUID
    status: Literal["active", "disabled"]
    status_reason: str | None
    market: SignalSubscriptionMarketResponse
    preset: SignalSubscriptionPresetResponse
    activated_at: datetime
    disabled_at: datetime | None


class SignalSubscriptionEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    subscription: SignalSubscriptionResponse


class SignalSubscriptionListEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    subscriptions: list[SignalSubscriptionResponse]
