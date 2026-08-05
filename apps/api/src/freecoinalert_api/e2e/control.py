"""Internal-only E2E fixture and worker-gate control service."""

from __future__ import annotations

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.models.historical_analysis_run import HistoricalAnalysisRun
from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.models.price_alert import PriceAlert
from freecoinalert_api.db.models.signal_event import SignalEvent
from freecoinalert_api.db.models.signal_subscription import SignalSubscription
from freecoinalert_api.db.models.telegram_connection import TelegramConnection
from freecoinalert_api.db.models.telegram_link_token import TelegramLinkToken
from freecoinalert_api.db.repositories.historical_analysis_datasets import (
    create_historical_analysis_dataset,
    create_historical_analysis_dataset_candles,
    get_historical_analysis_dataset_for_run,
    list_current_candles_for_historical_dataset,
)
from freecoinalert_api.db.repositories.historical_analysis_runs import (
    create_historical_analysis_run,
    get_historical_analysis_run_by_user_and_idempotency_key,
)
from freecoinalert_api.db.repositories.signal_presets import get_active_preset_by_code_version
from freecoinalert_api.db.repositories.signal_events import (
    create_signal_event,
    create_signal_event_invalidation,
)
from freecoinalert_api.db.repositories.supported_markets import get_supported_market
from freecoinalert_api.db.repositories.users import get_user_by_id
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.e2e import require_e2e_mode
from freecoinalert_api.e2e.worker_gate import (
    HISTORICAL_ANALYSIS_BEFORE_RUN_GATE,
    clear_gates,
    release_gates,
    set_gates,
)
from freecoinalert_api.historical_analysis.datasets import (
    calculate_historical_dataset_fingerprint,
    dataset_candle_from_manifest,
    manifest_candle_from_market,
    resolve_historical_dataset_bounds,
)
from freecoinalert_api.historical_analysis.engine import (
    ASSUMPTION_VERSION,
    ENGINE_VERSION,
)
from freecoinalert_api.historical_analysis.service import (
    SUPPORTED_CALCULATION_VERSIONS,
)
from freecoinalert_api.schemas.auth import to_camel_case


DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_SYMBOLS_BY_SCENARIO = {
    "analysis-positive": "ETHUSDT",
    "analysis-negative": "SOLUSDT",
    "analysis-zero-trade": "XRPUSDT",
    "analysis-paginated": "BNBUSDT",
    "analysis-missing-coverage": DEFAULT_SYMBOL,
}
DEFAULT_PRESET_CODE = "price_sma_200_cross_above_1h"
DEFAULT_PRESETS_BY_SCENARIO = {
    "analysis-positive": "price_sma_200_cross_above_1h",
    "analysis-negative": "price_sma_200_cross_above_1h",
    "analysis-zero-trade": "price_sma_200_cross_below_4h",
    "analysis-paginated": "price_sma_200_cross_above_1h",
    "analysis-missing-coverage": "price_sma_200_cross_above_1h",
}
FIXTURE_NAMESPACE = uuid.UUID("1da0f9a8-45a8-4d22-9b22-f3b9da0c9bb0")
PRICE_ALERT_FIXTURE_NAMESPACE = uuid.UUID("2d4c3ac7-6af2-4e6c-b30b-8d66f90f2f8d")
SIGNAL_FIXTURE_NAMESPACE = uuid.UUID("75cb7d53-2833-45b2-83ac-51cc2bc84a4e")


class HistoricalFixtureRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    user_id: uuid.UUID
    scenario: Literal[
        "analysis-positive",
        "analysis-negative",
        "analysis-zero-trade",
        "analysis-paginated",
        "analysis-missing-coverage",
    ] = "analysis-positive"
    symbol: str | None = None
    preset_code: str | None = None
    preset_version: int = Field(default=1, ge=1)
    range_days: int | None = Field(default=None, ge=7, le=90)


class WorkerGateRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    names: list[str] = Field(
        default_factory=lambda: [HISTORICAL_ANALYSIS_BEFORE_RUN_GATE],
        min_length=1,
    )


class OwnerFixtureRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        populate_by_name=True,
        extra="forbid",
    )

    user_id: uuid.UUID


class PriceAlertFixtureRequest(OwnerFixtureRequest):
    symbol: str = DEFAULT_SYMBOL
    count: int = Field(default=25, ge=1, le=100)
    status: Literal["active", "disabled"] = "disabled"


class SignalFeedFixtureRequest(OwnerFixtureRequest):
    symbol: str = DEFAULT_SYMBOL
    preset_code: str = DEFAULT_PRESET_CODE
    preset_version: int = Field(default=1, ge=1)
    count: int = Field(default=25, ge=1, le=200)
    invalidated_count: int = Field(default=0, ge=0, le=200)


class SignalInvalidationFixtureRequest(OwnerFixtureRequest):
    symbol: str = DEFAULT_SYMBOL
    preset_code: str = DEFAULT_PRESET_CODE
    preset_version: int = Field(default=1, ge=1)


def create_control_app(settings: Settings) -> FastAPI:
    require_e2e_mode(settings)
    app = FastAPI(title="FreeCoinAlert E2E control", docs_url=None, redoc_url=None)
    app.state.e2e_sequence = 0

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {"status": "ok", "e2e": True}

    @app.post("/__e2e/historical-worker/gates")
    async def gate_worker(
        request: WorkerGateRequest,
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        set_gates(settings, request.names)
        return {**_acknowledge(app), "gates": request.names}

    @app.post("/__e2e/historical-worker/release")
    async def release_worker(
        request: WorkerGateRequest,
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        release_gates(settings, request.names)
        return {**_acknowledge(app), "released": request.names}

    @app.post("/__e2e/reset")
    async def reset(
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        clear_gates(settings)
        return _acknowledge(app)

    @app.post("/__e2e/fixtures/historical-analysis")
    async def historical_analysis_fixture(
        request: HistoricalFixtureRequest,
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        fixture = await _create_historical_fixture(settings, request)
        return {**_acknowledge(app), **fixture}

    @app.post("/__e2e/fixtures/expire-telegram-link")
    async def expire_telegram_link(
        request: OwnerFixtureRequest,
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        await _expire_telegram_link(request.user_id)
        return {**_acknowledge(app), "expired": True}

    @app.post("/__e2e/fixtures/price-alerts")
    async def price_alert_fixture(
        request: PriceAlertFixtureRequest,
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        fixture = await _create_price_alert_fixture(request)
        return {**_acknowledge(app), **fixture}

    @app.post("/__e2e/fixtures/signal-feed")
    async def signal_feed_fixture(
        request: SignalFeedFixtureRequest,
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        fixture = await _create_signal_feed_fixture(settings, request)
        return {**_acknowledge(app), **fixture}

    @app.post("/__e2e/fixtures/invalidate-signal")
    async def invalidate_signal_fixture(
        request: SignalInvalidationFixtureRequest,
        x_e2e_control_token: str | None = Header(default=None),
    ) -> dict[str, object]:
        _authorize(settings, x_e2e_control_token)
        fixture = await _invalidate_latest_signal_fixture(request)
        return {**_acknowledge(app), **fixture}

    return app


async def _expire_telegram_link(user_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    async with get_async_session_factory()() as session:
        token = await session.scalar(
            select(TelegramLinkToken)
            .where(
                TelegramLinkToken.user_id == user_id,
                TelegramLinkToken.consumed_at.is_(None),
                TelegramLinkToken.revoked_at.is_(None),
            )
            .order_by(TelegramLinkToken.expires_at.desc())
        )
        if token is None:
            raise HTTPException(status_code=404, detail="The E2E Telegram link does not exist.")
        token.created_at = now - timedelta(seconds=2)
        token.expires_at = now - timedelta(seconds=1)
        await session.commit()


async def _create_price_alert_fixture(request: PriceAlertFixtureRequest) -> dict[str, object]:
    now = datetime.now(UTC)
    async with get_async_session_factory()() as session:
        user = await get_user_by_id(session, user_id=request.user_id)
        market = await get_supported_market(
            session,
            exchange="binance",
            market_type="spot",
            symbol=request.symbol,
        )
        connection = await session.scalar(
            select(TelegramConnection).where(
                TelegramConnection.user_id == request.user_id,
                TelegramConnection.status.in_(("connected", "degraded")),
            )
        )
        if user is None or market is None or connection is None:
            raise HTTPException(status_code=422, detail="The requested E2E fixture is unavailable.")
        if market.base_asset is None or market.quote_asset is None or market.price_tick is None:
            raise HTTPException(status_code=422, detail="The requested E2E fixture is unavailable.")

        for index in range(request.count):
            alert_id = uuid.uuid5(
                PRICE_ALERT_FIXTURE_NAMESPACE,
                f"{request.user_id}:{request.symbol}:{index}",
            )
            existing = await session.get(PriceAlert, alert_id)
            if existing is not None:
                continue
            created_at = now - timedelta(seconds=index + 1)
            session.add(
                PriceAlert(
                    id=alert_id,
                    user_id=request.user_id,
                    supported_market_id=market.id,
                    telegram_connection_id=connection.id,
                    creation_idempotency_key=f"e2e-price-alert:{request.user_id}:{request.symbol}:{index}",
                    kind="price_cross",
                    direction="cross_above",
                    target_price=Decimal("100") + Decimal(index),
                    exchange_snapshot=market.exchange,
                    market_type_snapshot=market.market_type,
                    symbol_snapshot=market.symbol,
                    base_asset_snapshot=market.base_asset,
                    quote_asset_snapshot=market.quote_asset,
                    price_tick_snapshot=market.price_tick,
                    status=request.status,
                    status_reason="e2e_fixture",
                    disabled_at=created_at if request.status == "disabled" else None,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
        await session.commit()
    return {"count": request.count, "status": request.status}


async def _create_signal_feed_fixture(
    settings: Settings,
    request: SignalFeedFixtureRequest,
) -> dict[str, object]:
    now = (settings.e2e_clock_now or datetime.now(UTC)).astimezone(UTC)
    async with get_async_session_factory()() as session:
        user = await get_user_by_id(session, user_id=request.user_id)
        market = await get_supported_market(
            session,
            exchange="binance",
            market_type="spot",
            symbol=request.symbol,
        )
        preset = await get_active_preset_by_code_version(
            session,
            code=request.preset_code,
            version=request.preset_version,
        )
        if user is None or market is None or preset is None:
            raise HTTPException(status_code=422, detail="The requested E2E fixture is unavailable.")
        if market.base_asset is None or market.quote_asset is None:
            raise HTTPException(status_code=422, detail="The requested E2E fixture is unavailable.")

        candles = list(
            (
                await session.scalars(
                    select(MarketCandle)
                    .where(
                        MarketCandle.supported_market_id == market.id,
                        MarketCandle.timeframe == preset.timeframe,
                        MarketCandle.status == "complete",
                        MarketCandle.is_current.is_(True),
                    )
                    .order_by(MarketCandle.open_time.desc())
                    .limit(request.count)
                )
            ).all()
        )
        if len(candles) < request.count:
            raise HTTPException(status_code=409, detail="The deterministic E2E candle seed is incomplete.")

        created = 0
        for index, candle in enumerate(candles):
            trigger_identity = str(
                uuid.uuid5(
                    SIGNAL_FIXTURE_NAMESPACE,
                    f"{request.user_id}:{preset.id}:{candle.id}",
                )
            )
            event = await create_signal_event(
                session,
                values={
                    "supported_market_id": market.id,
                    "signal_preset_id": preset.id,
                    "trigger_candle_id": candle.id,
                    "event_type": "preset_crossed",
                    "trigger_identity": trigger_identity,
                    "exchange_snapshot": market.exchange,
                    "market_type_snapshot": market.market_type,
                    "symbol_snapshot": market.symbol,
                    "base_asset_snapshot": market.base_asset,
                    "quote_asset_snapshot": market.quote_asset,
                    "preset_code_snapshot": preset.code,
                    "preset_version_snapshot": preset.version,
                    "preset_name_snapshot": preset.name,
                    "strategy_type_snapshot": preset.strategy_type,
                    "calculation_version_snapshot": "e2e_fixture_v1",
                    "timeframe_snapshot": preset.timeframe,
                    "direction_snapshot": preset.direction,
                    "period_snapshot": preset.period,
                    "threshold_snapshot": preset.threshold,
                    "price_input_snapshot": preset.price_input,
                    "candle_revision": candle.revision,
                    "candle_open_time": candle.open_time,
                    "candle_close_time": candle.close_time,
                    "previous_left_value": Decimal("99"),
                    "previous_right_value": Decimal("100"),
                    "current_left_value": Decimal("101"),
                    "current_right_value": Decimal("100"),
                    "candle_close_price": candle.close_price,
                    "backfilled": False,
                    "occurred_at": now - timedelta(seconds=index),
                },
            )
            if event is None:
                continue
            created += 1
            if index < request.invalidated_count:
                await create_signal_event_invalidation(
                    session,
                    signal_event_id=event.id,
                    reason="candle_corrected",
                    replacement_candle_id=None,
                    replacement_candle_revision=None,
                )
        await session.commit()
    return {"count": created, "invalidatedCount": min(created, request.invalidated_count)}


async def _invalidate_latest_signal_fixture(
    request: SignalInvalidationFixtureRequest,
) -> dict[str, object]:
    async with get_async_session_factory()() as session:
        event = await session.scalar(
            select(SignalEvent)
            .join(
                SignalSubscription,
                (SignalSubscription.supported_market_id == SignalEvent.supported_market_id)
                & (SignalSubscription.signal_preset_id == SignalEvent.signal_preset_id),
            )
            .where(
                SignalSubscription.user_id == request.user_id,
                SignalSubscription.status.in_(("active", "disabled")),
                SignalEvent.symbol_snapshot == request.symbol,
                SignalEvent.preset_code_snapshot == request.preset_code,
                SignalEvent.preset_version_snapshot == request.preset_version,
            )
            .order_by(SignalEvent.stream_sequence.desc())
        )
        if event is None:
            raise HTTPException(status_code=404, detail="The E2E signal does not exist.")
        invalidated = await create_signal_event_invalidation(
            session,
            signal_event_id=event.id,
            reason="candle_corrected",
            replacement_candle_id=None,
            replacement_candle_revision=None,
        )
        await session.commit()
    return {"invalidated": invalidated}


async def _create_historical_fixture(
    settings: Settings,
    request: HistoricalFixtureRequest,
) -> dict[str, object]:
    if settings.e2e_clock_now is None:
        raise HTTPException(status_code=500, detail="E2E_CLOCK_NOW is not configured.")
    now = settings.e2e_clock_now.astimezone(UTC)
    symbol = request.symbol or DEFAULT_SYMBOLS_BY_SCENARIO[request.scenario]
    preset_code = request.preset_code or DEFAULT_PRESETS_BY_SCENARIO[request.scenario]
    idempotency_key = uuid.uuid5(
        FIXTURE_NAMESPACE,
        ":".join(
            (
                str(request.user_id),
                request.scenario,
                symbol,
                preset_code,
                str(request.preset_version),
                str(request.range_days),
            )
        ),
    )

    async with get_async_session_factory()() as session:
        user = await get_user_by_id(session, user_id=request.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="The E2E fixture owner does not exist.")
        existing = await get_historical_analysis_run_by_user_and_idempotency_key(
            session,
            user_id=request.user_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return await _fixture_response(session, existing, request.scenario)

        market = await get_supported_market(
            session,
            exchange="binance",
            market_type="spot",
            symbol=symbol,
        )
        preset = await get_active_preset_by_code_version(
            session,
            code=preset_code,
            version=request.preset_version,
        )
        if market is None or preset is None or market.base_asset is None or market.quote_asset is None:
            raise HTTPException(status_code=422, detail="The requested E2E fixture is unavailable.")

        analysis_start, analysis_end = _analysis_range(
            now,
            preset.timeframe,
            range_days=request.range_days or _scenario_range_days(request.scenario),
        )
        calculation_version = SUPPORTED_CALCULATION_VERSIONS[preset.strategy_type]
        market_id = market.id
        market_exchange = market.exchange
        market_type = market.market_type
        market_symbol = market.symbol
        market_base_asset = market.base_asset
        market_quote_asset = market.quote_asset
        preset_id = preset.id
        preset_code_snapshot = preset.code
        preset_version_snapshot = preset.version
        preset_name_snapshot = preset.name
        preset_strategy_type = preset.strategy_type
        preset_timeframe = preset.timeframe
        preset_direction = preset.direction
        preset_period = preset.period
        preset_threshold = preset.threshold
        preset_price_input = preset.price_input
        await session.rollback()
        async with session.begin():
            run = await create_historical_analysis_run(
                session,
                user_id=request.user_id,
                supported_market_id=market_id,
                signal_preset_id=preset_id,
                idempotency_key=idempotency_key,
                exchange_snapshot=market_exchange,
                market_type_snapshot=market_type,
                symbol_snapshot=market_symbol,
                base_asset_snapshot=market_base_asset,
                quote_asset_snapshot=market_quote_asset,
                preset_code_snapshot=preset_code_snapshot,
                preset_version_snapshot=preset_version_snapshot,
                preset_name_snapshot=preset_name_snapshot,
                strategy_type_snapshot=preset_strategy_type,
                timeframe_snapshot=preset_timeframe,
                direction_snapshot=preset_direction,
                period_snapshot=preset_period,
                threshold_snapshot=preset_threshold,
                price_input_snapshot=preset_price_input,
                calculation_version_snapshot=calculation_version,
                simulation_version=ENGINE_VERSION,
                assumption_version=ASSUMPTION_VERSION,
                analysis_start=analysis_start,
                analysis_end=analysis_end,
                available_at=now,
            )
            bounds = resolve_historical_dataset_bounds(run)
            if request.scenario == "analysis-missing-coverage":
                dataset = await _create_terminal_dataset(
                    session,
                    run=run,
                    bounds=bounds,
                    now=now,
                )
                return {
                    "runId": str(run.id),
                    "datasetId": str(dataset.id),
                    "reportId": None,
                    "scenario": request.scenario,
                    "analysisStart": analysis_start.isoformat(),
                    "analysisEnd": analysis_end.isoformat(),
                }

            candles = list(
                await list_current_candles_for_historical_dataset(
                    session,
                    supported_market_id=market_id,
                    timeframe=bounds.timeframe,
                    start_open_time=bounds.warmup_start,
                    end_open_time=bounds.analysis_end,
                    limit=2_501,
                )
            )
            if len(candles) != bounds.expected_total_candles:
                raise HTTPException(
                    status_code=409,
                    detail="The deterministic E2E candle seed is not complete.",
                )
            manifest = tuple(
                manifest_candle_from_market(candle, bounds=bounds) for candle in candles
            )
            dataset_fingerprint = calculate_historical_dataset_fingerprint(
                run=run,
                bounds=bounds,
                candles=manifest,
            )
            dataset = await create_historical_analysis_dataset(
                session,
                run_id=run.id,
                supported_market_id=market_id,
                signal_preset_id=preset_id,
                status="ready",
                failure_code=None,
                timeframe=bounds.timeframe,
                analysis_start=bounds.analysis_start,
                analysis_end=bounds.analysis_end,
                warmup_start=bounds.warmup_start,
                required_warmup_candles=bounds.required_warmup_candles,
                warmup_candle_count=bounds.required_warmup_candles,
                analysis_candle_count=bounds.expected_analysis_candles,
                total_candle_count=bounds.expected_total_candles,
                first_open_time=candles[0].open_time,
                last_close_time=candles[-1].close_time,
                manifest_fingerprint=dataset_fingerprint,
                prepared_at=now,
            )
            await create_historical_analysis_dataset_candles(
                session,
                snapshots=tuple(
                    dataset_candle_from_manifest(
                        dataset_id=dataset.id,
                        position=position,
                        candle=candle,
                    )
                    for position, candle in enumerate(manifest)
                ),
            )
            return {
                "runId": str(run.id),
                "datasetId": str(dataset.id),
                "reportId": None,
                "scenario": request.scenario,
                "analysisStart": analysis_start.isoformat(),
                "analysisEnd": analysis_end.isoformat(),
            }


async def _fixture_response(session, run: HistoricalAnalysisRun, scenario: str) -> dict[str, object]:
    dataset = await get_historical_analysis_dataset_for_run(session, run_id=run.id)
    return {
        "runId": str(run.id),
        "datasetId": None if dataset is None else str(dataset.id),
        "reportId": None,
        "scenario": scenario,
        "analysisStart": run.analysis_start.isoformat(),
        "analysisEnd": run.analysis_end.isoformat(),
    }


async def _create_terminal_dataset(session, *, run, bounds, now):
    fingerprint = calculate_historical_dataset_fingerprint(
        run=run,
        bounds=bounds,
        candles=(),
    )
    return await create_historical_analysis_dataset(
        session,
        run_id=run.id,
        supported_market_id=run.supported_market_id,
        signal_preset_id=run.signal_preset_id,
        status="failed",
        failure_code="historical_dataset_gap_detected",
        timeframe=bounds.timeframe,
        analysis_start=bounds.analysis_start,
        analysis_end=bounds.analysis_end,
        warmup_start=bounds.warmup_start,
        required_warmup_candles=bounds.required_warmup_candles,
        warmup_candle_count=0,
        analysis_candle_count=0,
        total_candle_count=0,
        first_open_time=bounds.warmup_start,
        last_close_time=bounds.analysis_end,
        manifest_fingerprint=fingerprint,
        prepared_at=now,
    )


def _analysis_range(
    now: datetime,
    timeframe: str,
    *,
    range_days: int,
) -> tuple[datetime, datetime]:
    analysis_end = now.replace(minute=0, second=0, microsecond=0)
    if timeframe == "4h":
        analysis_end = analysis_end.replace(hour=analysis_end.hour - analysis_end.hour % 4)
    analysis_end -= timedelta(hours=24)
    analysis_start = analysis_end - timedelta(days=range_days)
    return analysis_start, analysis_end


def _scenario_range_days(scenario: str) -> int:
    return 90 if scenario == "analysis-paginated" else 14


def _authorize(settings: Settings, supplied_token: str | None) -> None:
    if not settings.e2e_control_token or not supplied_token or not hmac.compare_digest(
        supplied_token,
        settings.e2e_control_token,
    ):
        raise HTTPException(status_code=404, detail="Not found.")


def _acknowledge(app: FastAPI) -> dict[str, object]:
    app.state.e2e_sequence += 1
    return {"accepted": True, "sequence": app.state.e2e_sequence}


def main() -> None:
    settings = get_settings()
    uvicorn.run(create_control_app(settings), host="0.0.0.0", port=9100, log_level="info")


if __name__ == "__main__":
    main()
