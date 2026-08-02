import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.auth.principal import (
    AuthenticatedPrincipal,
    require_authenticated_principal,
    require_csrf_protected_principal,
)
from freecoinalert_api.core.config import (
    AuthenticationSettings,
    Settings,
    get_authentication_settings,
    get_settings,
)
from freecoinalert_api.db.repositories.auth_sessions import get_active_session_by_id
from freecoinalert_api.db.session import get_async_session_factory, get_database_session
from freecoinalert_api.schemas.signals import SignalPresetEnvelope, SignalSubscriptionCreateRequest, SignalSubscriptionEnvelope
from freecoinalert_api.signals.errors import SignalError
from freecoinalert_api.signals.feed import (
    SignalFeedReplayPlan,
    auth_expired_sse_message,
    parse_feed_limit,
    parse_feed_status,
    reset_sse_message,
    resolve_stream_cursor,
    signal_feed_service,
    stream_sse_event,
)
from freecoinalert_api.signals.feed_connections import (
    QueueItem,
    ResetSignal,
    SignalFeedConnection,
    SignalFeedConnectionManager,
)
from freecoinalert_api.signals.rate_limit import (
    disable_user_key,
    enable_ip_key,
    enable_user_key,
    feed_history_user_key,
    feed_stream_ip_key,
    feed_stream_user_key,
    signal_feed_rate_limiter,
    signal_rate_limiter,
)
from freecoinalert_api.signals.subscriptions import signal_subscription_service

logger = logging.getLogger(__name__)
signals_router = APIRouter(tags=["signals"])


@signals_router.get("/signal-presets")
async def list_signal_presets(database_session: AsyncSession = Depends(get_database_session)) -> JSONResponse:
    response_body = SignalPresetEnvelope(presets=await signal_subscription_service.list_presets(database_session))
    return JSONResponse(status_code=200, content=response_body.model_dump(mode="json", by_alias=True), headers={"Cache-Control": "public, max-age=60"})


@signals_router.get("/signal-subscriptions")
async def list_signal_subscriptions(authenticated_principal: AuthenticatedPrincipal = Depends(require_authenticated_principal), database_session: AsyncSession = Depends(get_database_session)) -> JSONResponse:
    response_body = await signal_subscription_service.list_for_user(database_session, user_id=authenticated_principal.user_id)
    return JSONResponse(status_code=200, content=response_body.model_dump(mode="json", by_alias=True), headers={"Cache-Control": "no-store"})


@signals_router.get("/signal-feed")
async def list_signal_feed(
    request: Request,
    authenticated_principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    limit = parse_feed_limit(request.query_params.get("limit"))
    feed_status = parse_feed_status(request.query_params.get("status"))
    await signal_feed_rate_limiter.consume(
        feed_history_user_key(str(authenticated_principal.user_id)),
        limit=120,
    )
    response_body = await signal_feed_service.list_history(
        database_session,
        user_id=authenticated_principal.user_id,
        limit=limit,
        cursor=request.query_params.get("cursor"),
        status=feed_status,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@signals_router.get("/signal-feed/stream")
async def stream_signal_feed(
    request: Request,
    authenticated_principal: AuthenticatedPrincipal = Depends(require_authenticated_principal),
    settings: AuthenticationSettings = Depends(get_authentication_settings),
) -> StreamingResponse:
    resume_sequence = resolve_stream_cursor(
        last_event_id=request.headers.get("Last-Event-ID"),
        after=request.query_params.get("after"),
    )
    client_address = "unknown" if request.client is None else request.client.host
    await signal_feed_rate_limiter.consume(
        feed_stream_user_key(str(authenticated_principal.user_id)),
        limit=10,
    )
    await signal_feed_rate_limiter.consume(
        feed_stream_ip_key(client_address),
        limit=30,
    )
    connection_manager = get_signal_feed_connection_manager(request)
    connection = await connection_manager.open(user_id=authenticated_principal.user_id)
    try:
        async with get_async_session_factory()() as session:
            replay_plan = await signal_feed_service.prepare_replay(
                session,
                user_id=authenticated_principal.user_id,
                after_sequence=resume_sequence,
            )
    except Exception:
        await connection_manager.close(connection, category="replay_unavailable")
        raise

    return StreamingResponse(
        signal_feed_stream_body(
            request=request,
            authenticated_principal=authenticated_principal,
            settings=settings,
            connection_manager=connection_manager,
            connection=connection,
            replay_plan=replay_plan,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


def get_signal_feed_connection_manager(request: Request) -> SignalFeedConnectionManager:
    return request.app.state.signal_feed_connection_manager


async def signal_feed_stream_body(
    *,
    request: Request,
    authenticated_principal: AuthenticatedPrincipal,
    settings: AuthenticationSettings,
    connection_manager: SignalFeedConnectionManager,
    connection: SignalFeedConnection,
    replay_plan: SignalFeedReplayPlan,
) -> AsyncGenerator[str, None]:
    del request
    close_category = "client_disconnected"
    try:
        yield "retry: 5000\n\n"
        if replay_plan.reset_required:
            close_category = "reset"
            yield reset_sse_message()
            return
        for record in replay_plan.records:
            logger.info(
                "signal.feed.event_sent user_id=%s sequence=%s kind=%s delivery_mode=replay",
                authenticated_principal.user_id,
                record.stream_event.sequence,
                record.stream_event.kind,
            )
            yield stream_sse_event(record, delivery_mode="replay")
            connection.mark_delivered(record.stream_event.sequence)
        connection.finish_replay(replay_plan.high_water_sequence)
        logger.info(
            "signal.feed.replay_completed user_id=%s replay_count=%s high_water_sequence=%s",
            authenticated_principal.user_id,
            len(replay_plan.records),
            replay_plan.high_water_sequence,
        )
        next_revalidation = asyncio.get_running_loop().time() + settings.signal_sse_session_revalidation_seconds
        while True:
            try:
                item: QueueItem = await asyncio.wait_for(
                    connection.queue.get(),
                    timeout=settings.signal_sse_heartbeat_seconds,
                )
            except TimeoutError:
                now = asyncio.get_running_loop().time()
                if now >= next_revalidation:
                    try:
                        session_active = await authenticated_session_is_active(authenticated_principal)
                    except Exception:
                        close_category = "auth_revalidation_failed"
                        logger.warning(
                            "signal.feed.reset_required user_id=%s reason=auth_revalidation_failed",
                            authenticated_principal.user_id,
                        )
                        yield reset_sse_message()
                        return
                    if not session_active:
                        close_category = "auth_expired"
                        logger.info(
                            "signal.feed.auth_expired user_id=%s session_id=%s",
                            authenticated_principal.user_id,
                            authenticated_principal.session_id,
                        )
                        yield auth_expired_sse_message()
                        return
                    next_revalidation = now + settings.signal_sse_session_revalidation_seconds
                yield ": heartbeat\n\n"
                continue
            try:
                if isinstance(item, ResetSignal):
                    close_category = "reset"
                    yield reset_sse_message()
                    return
                connection.mark_delivered(item)
                async with get_async_session_factory()() as session:
                    record = await signal_feed_service.stream_record_for_user(
                        session,
                        user_id=authenticated_principal.user_id,
                        sequence=item,
                    )
                if record is None:
                    continue
                logger.info(
                    "signal.feed.event_sent user_id=%s sequence=%s kind=%s delivery_mode=live",
                    authenticated_principal.user_id,
                    item,
                    record.stream_event.kind,
                )
                yield stream_sse_event(record, delivery_mode="live")
            except SignalError:
                close_category = "feed_unavailable"
                yield reset_sse_message()
                return
            except Exception:
                close_category = "feed_unavailable"
                logger.warning(
                    "signal.feed.reset_required user_id=%s reason=feed_unavailable",
                    authenticated_principal.user_id,
                )
                yield reset_sse_message()
                return
            finally:
                connection.queue.task_done()
    except asyncio.CancelledError:
        close_category = "client_disconnected"
        raise
    finally:
        await connection_manager.close(connection, category=close_category)


async def authenticated_session_is_active(
    authenticated_principal: AuthenticatedPrincipal,
) -> bool:
    async with get_async_session_factory()() as session:
        session_row = await get_active_session_by_id(
            session,
            session_id=authenticated_principal.session_id,
            user_id=authenticated_principal.user_id,
            current_time=datetime.now(UTC),
        )
    return session_row is not None
