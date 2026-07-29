from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


def to_camel_case(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class AuthenticationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    id: UUID
    email: str
    created_at: datetime


class AuthenticationResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)

    user: AuthenticatedUser
    csrf_token: str

