import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from freecoinalert_api.schemas.auth import to_camel_case

PriceAlertDirection = Literal["cross_above", "cross_below"]
PriceAlertStatus = Literal["active", "triggered", "disabled", "failed"]
DeliveryStatus = Literal[
    "not_queued",
    "queued",
    "sending",
    "retrying",
    "sent",
    "failed",
    "outcome_unknown",
]


class PriceAlertCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exchange: StrictStr
    market_type: StrictStr
    symbol: StrictStr
    direction: PriceAlertDirection
    target_price: StrictStr = Field(max_length=64)


class PriceAlertMarketResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    exchange: str
    market_type: str
    symbol: str
    base_asset: str
    quote_asset: str


class PriceAlertTriggerResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    price: str
    occurred_at: datetime


class PriceAlertDeliveryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    status: DeliveryStatus
    sent_at: datetime | None = None
    failure_code: str | None = None


class PriceAlertResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    id: uuid.UUID
    type: Literal["price_cross"]
    market: PriceAlertMarketResponse
    direction: PriceAlertDirection
    target_price: str
    status: PriceAlertStatus
    status_reason: str | None = None
    evaluation_ready: bool
    last_observed_price: str | None = None
    created_at: datetime
    trigger: PriceAlertTriggerResponse | None = None
    delivery: PriceAlertDeliveryResponse


class PriceAlertEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    alert: PriceAlertResponse


class PriceAlertListEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    alerts: list[PriceAlertResponse]
    next_cursor: str | None = None
