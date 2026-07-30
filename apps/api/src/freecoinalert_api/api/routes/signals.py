import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.auth.principal import AuthenticatedPrincipal, require_authenticated_principal, require_csrf_protected_principal
from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.session import get_database_session
from freecoinalert_api.schemas.signals import SignalPresetEnvelope, SignalSubscriptionCreateRequest, SignalSubscriptionEnvelope
from freecoinalert_api.signals.errors import SignalError
from freecoinalert_api.signals.rate_limit import disable_user_key, enable_ip_key, enable_user_key, signal_rate_limiter
from freecoinalert_api.signals.subscriptions import signal_subscription_service

signals_router = APIRouter(tags=["signals"])


@signals_router.get("/signal-presets")
async def list_signal_presets(database_session: AsyncSession = Depends(get_database_session)) -> JSONResponse:
    response_body = SignalPresetEnvelope(presets=await signal_subscription_service.list_presets(database_session))
    return JSONResponse(status_code=200, content=response_body.model_dump(mode="json", by_alias=True), headers={"Cache-Control": "public, max-age=60"})


@signals_router.get("/signal-subscriptions")
async def list_signal_subscriptions(authenticated_principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), database_session: AsyncSession = Depends(get_database_session)) -> JSONResponse:
    response_body = await signal_subscription_service.list_for_user(database_session, user_id=authenticated_principal.user_id)
    return JSONResponse(status_code=200, content=response_body.model_dump(mode="json", by_alias=True), headers={"Cache-Control": "no-store"})


@signals_router.post("/signal-subscriptions")
async def enable_signal_subscription(request: Request, authenticated_principal: AuthenticatedPrincipal = Depends(require_csrf_protected_principal), database_session: AsyncSession = Depends(get_database_session), settings: Settings = Depends(get_settings)) -> JSONResponse:
    body = await subscription_request_body(request)
    await signal_rate_limiter.consume(enable_user_key(str(authenticated_principal.user_id)), limit=20)
    await signal_rate_limiter.consume(enable_ip_key(client_ip(request)), limit=40)
    enabled = await signal_subscription_service.enable(database_session, user_id=authenticated_principal.user_id, request=body, market_catalog_max_age_seconds=settings.market_catalog_max_age_seconds)
    response_body = SignalSubscriptionEnvelope(subscription=await signal_subscription_service.response_for(database_session, enabled.subscription))
    return JSONResponse(status_code=enabled.status_code, content=response_body.model_dump(mode="json", by_alias=True), headers={"Cache-Control": "no-store"})


@signals_router.delete("/signal-subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_signal_subscription(subscription_id: str, response: Response, authenticated_principal: AuthenticatedPrincipal = Depends(require_csrf_protected_principal), database_session: AsyncSession = Depends(get_database_session)) -> Response:
    await signal_rate_limiter.consume(disable_user_key(str(authenticated_principal.user_id)), limit=30)
    await signal_subscription_service.disable(database_session, user_id=authenticated_principal.user_id, subscription_id=parse_subscription_id(subscription_id))
    response.headers["Cache-Control"] = "no-store"
    return response


async def subscription_request_body(request: Request) -> SignalSubscriptionCreateRequest:
    try:
        return SignalSubscriptionCreateRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        raise SignalError(status_code=422, code="SIGNAL_PRESET_UNAVAILABLE", message="The signal subscription request is invalid.") from None


def parse_subscription_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise SignalError(status_code=422, code="SIGNAL_PRESET_UNAVAILABLE", message="The signal subscription request is invalid.") from None


def client_ip(request: Request) -> str:
    return "unknown" if request.client is None else request.client.host
