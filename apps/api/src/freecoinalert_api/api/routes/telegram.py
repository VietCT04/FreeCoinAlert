from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.auth.principal import (
    AuthenticatedPrincipal,
    require_authenticated_principal,
    require_csrf_protected_principal,
)
from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.session import get_database_session
from freecoinalert_api.schemas.telegram import (
    TelegramConnectionEnvelope,
    TelegramConnectionResponse,
    TelegramLinkTokenResponse,
)
from freecoinalert_api.telegram.rate_limit import (
    disconnect_user_key,
    link_creation_ip_key,
    link_creation_user_key,
    telegram_rate_limiter,
)
from freecoinalert_api.telegram.service import telegram_connection_service

telegram_router = APIRouter(prefix="/telegram", tags=["telegram"])


@telegram_router.post("/link-tokens", status_code=status.HTTP_201_CREATED)
async def create_link_token(
    request: Request,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_csrf_protected_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    telegram_connection_service.require_configuration(settings)
    await telegram_rate_limiter.consume(
        link_creation_user_key(str(authenticated_principal.user_id)),
        limit=5,
    )
    await telegram_rate_limiter.consume(
        link_creation_ip_key(get_client_ip(request)),
        limit=10,
    )
    telegram_link = await telegram_connection_service.create_link(
        database_session,
        user_id=authenticated_principal.user_id,
        settings=settings,
    )
    response_body = TelegramLinkTokenResponse(
        connection=TelegramConnectionResponse(
            status=telegram_link.connection.status,
            link_expires_at=telegram_link.connection.link_expires_at,
        ),
        telegram_url=telegram_link.url,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@telegram_router.get("/connection")
async def get_connection(
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    connection = await telegram_connection_service.get_connection(
        database_session,
        user_id=authenticated_principal.user_id,
    )
    response_body = TelegramConnectionEnvelope(
        connection=TelegramConnectionResponse(
            status=connection.status,
            username=connection.username,
            connected_at=connection.connected_at,
            last_verified_at=connection.last_verified_at,
            link_expires_at=connection.link_expires_at,
            status_reason=connection.status_reason,
        )
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@telegram_router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_connection(
    response: Response,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_csrf_protected_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> Response:
    await telegram_rate_limiter.consume(
        disconnect_user_key(str(authenticated_principal.user_id)),
        limit=10,
    )
    await telegram_connection_service.disconnect(
        database_session,
        user_id=authenticated_principal.user_id,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    response.headers["Cache-Control"] = "no-store"
    return response


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"

    return request.client.host
