from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from freecoinalert_api.api.errors import auth_request_validation_exception_handler
from freecoinalert_api.api.router import api_router
from freecoinalert_api.core.config import get_authentication_settings


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
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(
        RequestValidationError,
        auth_request_validation_exception_handler,
    )
    app.include_router(api_router)
    return app


app = create_app()
