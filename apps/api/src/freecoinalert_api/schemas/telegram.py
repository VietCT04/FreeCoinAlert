from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from freecoinalert_api.schemas.auth import to_camel_case

TelegramConnectionStatus = Literal[
    "not_connected",
    "linking",
    "connected",
    "degraded",
    "disconnected",
]


class TelegramConnectionResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    status: TelegramConnectionStatus
    username: str | None = None
    connected_at: datetime | None = None
    last_verified_at: datetime | None = None
    link_expires_at: datetime | None = None
    status_reason: str | None = None


class TelegramConnectionEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    connection: TelegramConnectionResponse


class TelegramLinkTokenResponse(TelegramConnectionEnvelope):
    telegram_url: str
