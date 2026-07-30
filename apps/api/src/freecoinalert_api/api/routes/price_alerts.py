import uuid

from fastapi import APIRouter, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.alerts.rate_limit import (
    alert_rate_limiter,
    create_ip_key,
    create_user_key,
    delete_user_key,
)
from freecoinalert_api.alerts.service import (
    price_alert_service,
    request_invalid_error,
    validate_idempotency_key,
)
from freecoinalert_api.auth.principal import (
    AuthenticatedPrincipal,
    require_authenticated_principal,
    require_csrf_protected_principal,
)
from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.session import get_database_session
from freecoinalert_api.schemas.price_alerts import (
    PriceAlertCreateRequest,
    PriceAlertEnvelope,
)

price_alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


@price_alerts_router.post("/price")
async def create_price_alert(
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_csrf_protected_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    valid_idempotency_key = validate_idempotency_key(idempotency_key)
    request_body = await create_request_body(request)
    existing_alert = await price_alert_service.find_replay(
        database_session,
        user_id=authenticated_principal.user_id,
        idempotency_key=valid_idempotency_key,
        request=request_body,
    )
    if existing_alert is not None:
        response_body = PriceAlertEnvelope(
            alert=await price_alert_service.response_for(database_session, existing_alert)
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_body.model_dump(mode="json", by_alias=True),
            headers={"Cache-Control": "no-store"},
        )

    await alert_rate_limiter.consume(
        create_user_key(str(authenticated_principal.user_id)),
        limit=10,
    )
    await alert_rate_limiter.consume(create_ip_key(get_client_ip(request)), limit=30)
    created_alert = await price_alert_service.create(
        database_session,
        user_id=authenticated_principal.user_id,
        idempotency_key=valid_idempotency_key,
        request=request_body,
        market_catalog_max_age_seconds=settings.market_catalog_max_age_seconds,
    )
    response_body = PriceAlertEnvelope(
        alert=await price_alert_service.response_for(database_session, created_alert.alert)
    )
    return JSONResponse(
        status_code=(status.HTTP_200_OK if created_alert.replayed else status.HTTP_201_CREATED),
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@price_alerts_router.get("")
async def list_price_alerts(
    request: Request,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    response_body = await price_alert_service.list_response(
        database_session,
        user_id=authenticated_principal.user_id,
        limit_value=request.query_params.get("limit"),
        cursor_value=request.query_params.get("cursor"),
        status_value=request.query_params.get("status"),
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@price_alerts_router.get("/{alert_id}")
async def get_price_alert(
    alert_id: str,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    response_body = PriceAlertEnvelope(
        alert=await price_alert_service.get_response(
            database_session,
            user_id=authenticated_principal.user_id,
            alert_id=parse_alert_id(alert_id),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@price_alerts_router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_price_alert(
    alert_id: str,
    response: Response,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_csrf_protected_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> Response:
    await alert_rate_limiter.consume(
        delete_user_key(str(authenticated_principal.user_id)),
        limit=30,
    )
    await price_alert_service.delete(
        database_session,
        user_id=authenticated_principal.user_id,
        alert_id=parse_alert_id(alert_id),
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    response.headers["Cache-Control"] = "no-store"
    return response


async def create_request_body(request: Request) -> PriceAlertCreateRequest:
    try:
        body = await request.json()
        return PriceAlertCreateRequest.model_validate(body)
    except (ValueError, ValidationError):
        raise request_invalid_error() from None


def parse_alert_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise request_invalid_error() from None


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host
