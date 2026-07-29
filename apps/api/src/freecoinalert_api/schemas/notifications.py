import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from freecoinalert_api.schemas.auth import to_camel_case

NotificationStatus = Literal["queued", "sending", "retrying", "sent", "failed"]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    id: uuid.UUID
    status: NotificationStatus
    created_at: datetime
    sent_at: datetime | None = None
    failure_code: str | None = None


class NotificationEnvelope(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    notification: NotificationResponse
