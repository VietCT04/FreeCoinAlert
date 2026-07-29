from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AuthenticationError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        retry_after: int | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retry_after = retry_after


def authentication_error_response(error: AuthenticationError) -> JSONResponse:
    headers: dict[str, str] = {}

    if error.retry_after is not None:
        headers["Retry-After"] = str(error.retry_after)

    return JSONResponse(
        status_code=error.status_code,
        content={
            "code": error.code,
            "message": error.message,
            "details": [],
        },
        headers=headers,
    )


async def auth_request_validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    del exception

    if request.url.path.startswith("/auth/"):
        return authentication_error_response(
            AuthenticationError(
                status_code=422,
                code="AUTH_REQUEST_INVALID",
                message="The authentication request is invalid.",
            )
        )

    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation failed."},
    )

