from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.auth.principal import (
    AuthenticatedPrincipal,
    require_authenticated_principal,
    require_csrf_protected_principal,
)
from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.session import get_database_session
from freecoinalert_api.historical_analysis.rate_limit import (
    cancel_user_key,
    create_ip_key,
    create_user_key,
    historical_analysis_rate_limiter,
    read_user_key,
)
from freecoinalert_api.historical_analysis.reports import (
    historical_analysis_report_service,
)
from freecoinalert_api.historical_analysis.errors import request_invalid_error
from freecoinalert_api.historical_analysis.service import (
    configuration_response,
    historical_analysis_service,
    parse_run_id,
    validate_idempotency_key,
)
from freecoinalert_api.schemas.historical_analysis import (
    HistoricalAnalysisCreateRequest,
    HistoricalAnalysisEquityEnvelope,
    HistoricalAnalysisReportEnvelope,
    HistoricalAnalysisRunEnvelope,
    HistoricalAnalysisTradesEnvelope,
)

historical_analysis_router = APIRouter(tags=["historical-analysis"])


@historical_analysis_router.get("/historical-analysis/configuration")
async def get_historical_analysis_configuration(
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
) -> JSONResponse:
    await historical_analysis_rate_limiter.consume(
        read_user_key(str(authenticated_principal.user_id)),
        limit=120,
    )
    response_body = configuration_response()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@historical_analysis_router.post("/historical-analyses")
async def create_historical_analysis(
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
    existing_run = await historical_analysis_service.find_replay(
        database_session,
        user_id=authenticated_principal.user_id,
        idempotency_key=valid_idempotency_key,
        request=request_body,
    )
    if existing_run is not None:
        return run_response(
            historical_analysis_service.response_for(existing_run),
            status_code=status.HTTP_200_OK,
        )

    await historical_analysis_rate_limiter.consume(
        create_user_key(str(authenticated_principal.user_id)),
        limit=10,
    )
    await historical_analysis_rate_limiter.consume(
        create_ip_key(client_ip(request)),
        limit=30,
    )
    created = await historical_analysis_service.create(
        database_session,
        user_id=authenticated_principal.user_id,
        idempotency_key=valid_idempotency_key,
        request=request_body,
        settings=settings,
    )
    return run_response(
        historical_analysis_service.response_for(created.run),
        status_code=created.status_code,
    )


@historical_analysis_router.get("/historical-analyses")
async def list_historical_analyses(
    request: Request,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    await historical_analysis_rate_limiter.consume(
        read_user_key(str(authenticated_principal.user_id)),
        limit=120,
    )
    response_body = await historical_analysis_service.list_for_user(
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


@historical_analysis_router.get("/historical-analyses/{run_id}")
async def get_historical_analysis(
    run_id: str,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    await historical_analysis_rate_limiter.consume(
        read_user_key(str(authenticated_principal.user_id)),
        limit=120,
    )
    response_body = await historical_analysis_service.get_for_user(
        database_session,
        user_id=authenticated_principal.user_id,
        run_id=parse_run_id(run_id),
    )
    return run_response(response_body, status_code=status.HTTP_200_OK)


@historical_analysis_router.get("/historical-analyses/{run_id}/report")
async def get_historical_analysis_report(
    run_id: str,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    await historical_analysis_rate_limiter.consume(
        read_user_key(str(authenticated_principal.user_id)),
        limit=120,
    )
    response_body: HistoricalAnalysisReportEnvelope = (
        await historical_analysis_report_service.get_report_for_user(
            database_session,
            user_id=authenticated_principal.user_id,
            run_id=parse_run_id(run_id),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@historical_analysis_router.get("/historical-analyses/{run_id}/trades")
async def get_historical_analysis_trades(
    request: Request,
    run_id: str,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    await historical_analysis_rate_limiter.consume(
        read_user_key(str(authenticated_principal.user_id)),
        limit=120,
    )
    response_body: HistoricalAnalysisTradesEnvelope = (
        await historical_analysis_report_service.list_trades_for_user(
            database_session,
            user_id=authenticated_principal.user_id,
            run_id=parse_run_id(run_id),
            limit_value=request.query_params.get("limit"),
            cursor_value=request.query_params.get("cursor"),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@historical_analysis_router.get("/historical-analyses/{run_id}/equity")
async def get_historical_analysis_equity(
    request: Request,
    run_id: str,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_authenticated_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    await historical_analysis_rate_limiter.consume(
        read_user_key(str(authenticated_principal.user_id)),
        limit=120,
    )
    response_body: HistoricalAnalysisEquityEnvelope = (
        await historical_analysis_report_service.list_equity_for_user(
            database_session,
            user_id=authenticated_principal.user_id,
            run_id=parse_run_id(run_id),
            limit_value=request.query_params.get("limit"),
            cursor_value=request.query_params.get("cursor"),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


@historical_analysis_router.post("/historical-analyses/{run_id}/cancel")
async def cancel_historical_analysis(
    run_id: str,
    authenticated_principal: AuthenticatedPrincipal = Depends(
        require_csrf_protected_principal
    ),
    database_session: AsyncSession = Depends(get_database_session),
) -> JSONResponse:
    await historical_analysis_rate_limiter.consume(
        cancel_user_key(str(authenticated_principal.user_id)),
        limit=30,
    )
    response_body = await historical_analysis_service.cancel_for_user(
        database_session,
        user_id=authenticated_principal.user_id,
        run_id=parse_run_id(run_id),
    )
    return run_response(response_body, status_code=status.HTTP_200_OK)


async def create_request_body(request: Request) -> HistoricalAnalysisCreateRequest:
    try:
        return HistoricalAnalysisCreateRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        raise request_invalid_error() from None


def run_response(
    response_body: HistoricalAnalysisRunEnvelope,
    *,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "no-store"},
    )


def client_ip(request: Request) -> str:
    return "unknown" if request.client is None else request.client.host
