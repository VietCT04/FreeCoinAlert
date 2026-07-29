from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from freecoinalert_api.api.errors import (
    AuthenticationError,
    auth_request_validation_exception_handler,
    authentication_error_response,
)
from freecoinalert_api.api.router import api_router
from freecoinalert_api.core.config import get_authentication_settings


async def authentication_exception_handler(
    request: Request,
    exception: AuthenticationError,
) -> JSONResponse:
    del request
    return authentication_error_response(exception)


def create_app() -> FastAPI:
    settings = get_authentication_settings()
    app = FastAPI(
        title="FreeCoinAlert API",
        version="0.1.0",
        description="Backend API for the FreeCoinAlert platform.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    app.add_exception_handler(
        RequestValidationError,
        auth_request_validation_exception_handler,
    )
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.include_router(api_router)
    return app


app = create_app()
