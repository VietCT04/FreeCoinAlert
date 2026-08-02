from contextlib import asynccontextmanager

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
from freecoinalert_api.signals.feed_connections import SignalFeedConnectionManager
from freecoinalert_api.signals.feed_listener import SignalFeedListener


async def authentication_exception_handler(
    request: Request,
    exception: AuthenticationError,
) -> JSONResponse:
    del request
    return authentication_error_response(exception)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    listener = SignalFeedListener(
        connection_manager=app.state.signal_feed_connection_manager,
    )
    app.state.signal_feed_listener = listener
    await listener.start()
    try:
        yield
    finally:
        await listener.stop()


def create_app() -> FastAPI:
    settings = get_authentication_settings()
    app = FastAPI(
        title="FreeCoinAlert API",
        version="0.1.0",
        description="Backend API for the FreeCoinAlert platform.",
        lifespan=app_lifespan,
    )
    app.state.signal_feed_connection_manager = SignalFeedConnectionManager(
        max_connections_per_user=settings.signal_sse_max_connections_per_user,
        max_connections_per_process=settings.signal_sse_max_connections_per_process,
        queue_size=settings.signal_sse_queue_size,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=[
            "Content-Type",
            "Idempotency-Key",
            "Last-Event-ID",
            "X-CSRF-Token",
        ],
    )
    app.add_exception_handler(
        RequestValidationError,
        auth_request_validation_exception_handler,
    )
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.include_router(api_router)
    return app


app = create_app()
