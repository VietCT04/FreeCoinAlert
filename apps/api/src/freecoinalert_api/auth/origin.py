from fastapi import Request

from freecoinalert_api.api.errors import AuthenticationError
from freecoinalert_api.core.config import Settings


def validate_authentication_origin(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")

    if origin is None:
        return

    api_origin = str(request.base_url).rstrip("/")

    if origin == settings.web_origin or origin == api_origin:
        return

    raise AuthenticationError(
        status_code=403,
        code="AUTH_ORIGIN_REJECTED",
        message="The request origin is not allowed.",
    )

