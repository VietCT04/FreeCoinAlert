import base64
import binascii
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.core.config import Settings
from freecoinalert_api.db.models.historical_analysis_run import HistoricalAnalysisRun
from freecoinalert_api.db.models.signal_preset import SignalPreset
from freecoinalert_api.db.repositories.historical_analysis_runs import (
    count_active_historical_analysis_runs,
    create_historical_analysis_run,
    get_historical_analysis_run_by_user_and_idempotency_key,
    get_historical_analysis_run_for_user,
    list_historical_analysis_runs_page_for_user,
    lock_user_historical_analysis_creation,
)
from freecoinalert_api.db.repositories.signal_presets import (
    get_active_preset_by_code_version,
    get_preset_by_code_version,
)
from freecoinalert_api.db.repositories.supported_markets import get_supported_market
from freecoinalert_api.historical_analysis.engine import (
    ASSUMPTION_VERSION,
    ENGINE_VERSION,
)
from freecoinalert_api.market_data.catalog import utc_now
from freecoinalert_api.schemas.historical_analysis import (
    HistoricalAnalysisAssumptionsResponse,
    HistoricalAnalysisConfigurationResponse,
    HistoricalAnalysisCreateRequest,
    HistoricalAnalysisMarketSnapshotResponse,
    HistoricalAnalysisPresetParametersResponse,
    HistoricalAnalysisPresetSnapshotResponse,
    HistoricalAnalysisRunEnvelope,
    HistoricalAnalysisRunListEnvelope,
    HistoricalAnalysisRunResponse,
)
from freecoinalert_api.historical_analysis.errors import (
    HistoricalAnalysisError,
    active_limit_error,
    idempotency_conflict_error,
    market_not_found_error,
    not_found_error,
    preset_not_found_error,
    preset_unavailable_error,
    range_unavailable_error,
    request_invalid_error,
    unavailable_error,
)

logger = logging.getLogger(__name__)

MINIMUM_RANGE_DAYS = 7
MAXIMUM_RANGE_DAYS = 90
MAXIMUM_ACTIVE_RUNS = 2
SIMULATION_VERSION = ENGINE_VERSION

SUPPORTED_CALCULATION_VERSIONS = {
    "price_sma_cross": "sma_close_v1",
    "rsi_threshold_cross": "rsi_wilder_close_v1",
}
REQUIRED_WARMUP_CANDLES = {
    "price_sma_cross": 200,
    "rsi_threshold_cross": 15,
}
TIMEFRAME_HOURS = {"1h": 1, "4h": 4}
SUPPORTED_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}


@dataclass(frozen=True, slots=True)
class NormalizedHistoricalAnalysisRequest:
    exchange: str
    market_type: str
    symbol: str
    preset_code: str
    preset_version: int
    analysis_start: datetime
    analysis_end: datetime


@dataclass(frozen=True, slots=True)
class CreatedHistoricalAnalysisRun:
    run: HistoricalAnalysisRun
    status_code: int
    replayed: bool


class HistoricalAnalysisService:
    async def find_replay(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        idempotency_key: uuid.UUID,
        request: HistoricalAnalysisCreateRequest,
    ) -> HistoricalAnalysisRun | None:
        normalized = normalize_request(request)
        try:
            existing = await get_historical_analysis_run_by_user_and_idempotency_key(
                session,
                user_id=user_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                require_matching_replay(existing, normalized)
                logger.info(
                    "historical.analysis.create_replayed run_id=%s",
                    existing.id,
                )
            return existing
        except HistoricalAnalysisError:
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        idempotency_key: uuid.UUID,
        request: HistoricalAnalysisCreateRequest,
        settings: Settings,
    ) -> CreatedHistoricalAnalysisRun:
        normalized = normalize_request(request)
        try:
            await lock_user_historical_analysis_creation(session, user_id=user_id)
            existing = await get_historical_analysis_run_by_user_and_idempotency_key(
                session,
                user_id=user_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                require_matching_replay(existing, normalized)
                logger.info(
                    "historical.analysis.create_replayed run_id=%s",
                    existing.id,
                )
                return CreatedHistoricalAnalysisRun(
                    run=existing,
                    status_code=200,
                    replayed=True,
                )

            market = await get_supported_market(
                session,
                exchange=normalized.exchange,
                market_type=normalized.market_type,
                symbol=normalized.symbol,
            )
            if (
                market is None
                or not market.product_enabled
                or market.base_asset is None
                or market.quote_asset is None
            ):
                raise market_not_found_error()

            preset = await get_active_preset_by_code_version(
                session,
                code=normalized.preset_code,
                version=normalized.preset_version,
            )
            if preset is None:
                known_preset = await get_preset_by_code_version(
                    session,
                    code=normalized.preset_code,
                    version=normalized.preset_version,
                )
                if known_preset is None:
                    raise preset_not_found_error()
                raise preset_unavailable_error()

            calculation_version = resolve_calculation_version(preset)
            required_warmup_candles = resolve_required_warmup(preset)
            validate_range(
                normalized,
                timeframe=preset.timeframe,
                required_warmup_candles=required_warmup_candles,
                current_time=utc_now(),
                candle_retention_days=settings.candle_retention_days,
            )

            active_count = await count_active_historical_analysis_runs(
                session,
                user_id=user_id,
            )
            if active_count >= MAXIMUM_ACTIVE_RUNS:
                raise active_limit_error()

            now = utc_now()
            run = await create_historical_analysis_run(
                session,
                user_id=user_id,
                supported_market_id=market.id,
                signal_preset_id=preset.id,
                idempotency_key=idempotency_key,
                exchange_snapshot=market.exchange,
                market_type_snapshot=market.market_type,
                symbol_snapshot=market.symbol,
                base_asset_snapshot=market.base_asset,
                quote_asset_snapshot=market.quote_asset,
                preset_code_snapshot=preset.code,
                preset_version_snapshot=preset.version,
                preset_name_snapshot=preset.name,
                strategy_type_snapshot=preset.strategy_type,
                timeframe_snapshot=preset.timeframe,
                direction_snapshot=preset.direction,
                period_snapshot=preset.period,
                threshold_snapshot=preset.threshold,
                price_input_snapshot=preset.price_input,
                calculation_version_snapshot=calculation_version,
                simulation_version=SIMULATION_VERSION,
                assumption_version=ASSUMPTION_VERSION,
                analysis_start=normalized.analysis_start,
                analysis_end=normalized.analysis_end,
                available_at=now,
            )
            await session.commit()
        except HistoricalAnalysisError:
            await session.rollback()
            logger.info("historical.analysis.creation_rejected")
            raise
        except IntegrityError:
            await session.rollback()
            try:
                existing = await get_historical_analysis_run_by_user_and_idempotency_key(
                    session,
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                )
            except SQLAlchemyError:
                await session.rollback()
                raise unavailable_error() from None
            if existing is not None:
                require_matching_replay(existing, normalized)
                return CreatedHistoricalAnalysisRun(
                    run=existing,
                    status_code=200,
                    replayed=True,
                )
            raise unavailable_error() from None
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

        logger.info("historical.analysis.created run_id=%s", run.id)
        return CreatedHistoricalAnalysisRun(
            run=run,
            status_code=201,
            replayed=False,
        )

    async def list_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit_value: str | None,
        cursor_value: str | None,
        status_value: str | None,
    ) -> HistoricalAnalysisRunListEnvelope:
        limit = parse_limit(limit_value)
        status = parse_status(status_value)
        cursor_created_at, cursor_id = decode_cursor(cursor_value)
        try:
            runs = await list_historical_analysis_runs_page_for_user(
                session,
                user_id=user_id,
                limit=limit + 1,
                status=status,
                cursor_created_at=cursor_created_at,
                cursor_id=cursor_id,
            )
            page_runs = runs[:limit]
            next_cursor = None
            if len(runs) > limit:
                last_run = page_runs[-1]
                next_cursor = encode_cursor(last_run.created_at, last_run.id)
            return HistoricalAnalysisRunListEnvelope(
                runs=[self.response_for(run).run for run in page_runs],
                next_cursor=next_cursor,
            )
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def get_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> HistoricalAnalysisRunEnvelope:
        try:
            run = await get_historical_analysis_run_for_user(
                session,
                user_id=user_id,
                run_id=run_id,
            )
            if run is None:
                raise not_found_error()
            return self.response_for(run)
        except HistoricalAnalysisError:
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def cancel_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> HistoricalAnalysisRunEnvelope:
        try:
            run = await get_historical_analysis_run_for_user(
                session,
                user_id=user_id,
                run_id=run_id,
                for_update=True,
            )
            if run is None:
                raise not_found_error()

            now = utc_now()
            if run.status == "queued":
                run.status = "cancelled"
                run.progress_stage = "cancelled"
                run.cancellation_requested_at = now
                run.cancelled_at = now
            elif run.status == "running" and run.cancellation_requested_at is None:
                run.cancellation_requested_at = now

            await session.commit()
            logger.info(
                "historical.analysis.cancel_requested run_id=%s status=%s",
                run.id,
                run.status,
            )
            return self.response_for(run)
        except HistoricalAnalysisError:
            await session.rollback()
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    @staticmethod
    def response_for(run: HistoricalAnalysisRun) -> HistoricalAnalysisRunEnvelope:
        return HistoricalAnalysisRunEnvelope(
            run=HistoricalAnalysisRunResponse(
                id=run.id,
                status=run.status,
                market=HistoricalAnalysisMarketSnapshotResponse(
                    exchange=run.exchange_snapshot,
                    market_type=run.market_type_snapshot,
                    symbol=run.symbol_snapshot,
                    base_asset=run.base_asset_snapshot,
                    quote_asset=run.quote_asset_snapshot,
                ),
                preset=HistoricalAnalysisPresetSnapshotResponse(
                    code=run.preset_code_snapshot,
                    version=run.preset_version_snapshot,
                    name=run.preset_name_snapshot,
                    strategy_type=run.strategy_type_snapshot,
                    timeframe=run.timeframe_snapshot,
                    direction=run.direction_snapshot,
                    parameters=HistoricalAnalysisPresetParametersResponse(
                        period=run.period_snapshot,
                        threshold=(
                            None
                            if run.threshold_snapshot is None
                            else format(run.threshold_snapshot, "f")
                        ),
                        price_input=run.price_input_snapshot,
                    ),
                ),
                calculation_version=run.calculation_version_snapshot,
                simulation_version=run.simulation_version,
                assumption_version=run.assumption_version,
                analysis_start=run.analysis_start,
                analysis_end=run.analysis_end,
                progress_stage=run.progress_stage,
                progress_percent=run.progress_percent,
                cancellation_requested=run.cancellation_requested_at is not None,
                cancellation_requested_at=run.cancellation_requested_at,
                created_at=run.created_at,
                started_at=run.started_at,
                completed_at=run.completed_at,
                failed_at=run.failed_at,
                cancelled_at=run.cancelled_at,
                failure_code=run.failure_code,
            )
        )


def normalize_request(
    request: HistoricalAnalysisCreateRequest,
) -> NormalizedHistoricalAnalysisRequest:
    try:
        analysis_start = normalize_utc_datetime(request.analysis_start)
        analysis_end = normalize_utc_datetime(request.analysis_end)
    except ValueError:
        raise request_invalid_error() from None
    return NormalizedHistoricalAnalysisRequest(
        exchange=request.exchange,
        market_type=request.market_type,
        symbol=request.symbol,
        preset_code=request.preset_code,
        preset_version=request.preset_version,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
    )


def normalize_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("The analysis range must use UTC timestamps.")
    return value.astimezone(UTC)


def resolve_calculation_version(preset: SignalPreset) -> str:
    calculation_version = SUPPORTED_CALCULATION_VERSIONS.get(preset.strategy_type)
    if calculation_version is None:
        raise preset_unavailable_error()
    return calculation_version


def resolve_required_warmup(preset: SignalPreset) -> int:
    required_warmup = REQUIRED_WARMUP_CANDLES.get(preset.strategy_type)
    if required_warmup is None or preset.timeframe not in TIMEFRAME_HOURS:
        raise preset_unavailable_error()
    return required_warmup


def validate_range(
    request: NormalizedHistoricalAnalysisRequest,
    *,
    timeframe: str,
    required_warmup_candles: int,
    current_time: datetime,
    candle_retention_days: int,
) -> None:
    timeframe_hours = TIMEFRAME_HOURS.get(timeframe)
    if timeframe_hours is None:
        raise preset_unavailable_error()
    timeframe_delta = timedelta(hours=timeframe_hours)
    if not is_timeframe_boundary(request.analysis_start, timeframe_hours) or not is_timeframe_boundary(
        request.analysis_end,
        timeframe_hours,
    ):
        raise request_invalid_error()
    if request.analysis_end <= request.analysis_start:
        raise request_invalid_error()

    visible_range = request.analysis_end - request.analysis_start
    if visible_range < timedelta(days=MINIMUM_RANGE_DAYS) or visible_range > timedelta(
        days=MAXIMUM_RANGE_DAYS
    ):
        raise range_unavailable_error()

    latest_closed_boundary = latest_fully_closed_boundary(current_time, timeframe_hours)
    if request.analysis_end > latest_closed_boundary:
        raise range_unavailable_error()

    warmup_start = request.analysis_start - required_warmup_candles * timeframe_delta
    retention_cutoff = current_time - timedelta(days=candle_retention_days)
    if warmup_start < retention_cutoff:
        raise range_unavailable_error()


def is_timeframe_boundary(value: datetime, timeframe_hours: int) -> bool:
    return (
        value.minute == 0
        and value.second == 0
        and value.microsecond == 0
        and value.hour % timeframe_hours == 0
    )


def latest_fully_closed_boundary(current_time: datetime, timeframe_hours: int) -> datetime:
    return current_time.replace(
        hour=(current_time.hour // timeframe_hours) * timeframe_hours,
        minute=0,
        second=0,
        microsecond=0,
    )


def require_matching_replay(
    run: HistoricalAnalysisRun,
    request: NormalizedHistoricalAnalysisRequest,
) -> None:
    if (
        run.exchange_snapshot != request.exchange
        or run.market_type_snapshot != request.market_type
        or run.symbol_snapshot != request.symbol
        or run.preset_code_snapshot != request.preset_code
        or run.preset_version_snapshot != request.preset_version
        or run.analysis_start != request.analysis_start
        or run.analysis_end != request.analysis_end
    ):
        raise idempotency_conflict_error()


def validate_idempotency_key(value: str | None) -> uuid.UUID:
    if value is None or len(value) > 128:
        raise request_invalid_error()
    try:
        return uuid.UUID(value)
    except (AttributeError, ValueError):
        raise request_invalid_error() from None


def parse_run_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (AttributeError, ValueError):
        raise request_invalid_error() from None


def parse_limit(value: str | None) -> int:
    if value is None:
        return 20
    try:
        limit = int(value)
    except (TypeError, ValueError):
        raise request_invalid_error() from None
    if limit < 1 or limit > 100 or str(limit) != value:
        raise request_invalid_error()
    return limit


def parse_status(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in SUPPORTED_STATUSES:
        raise request_invalid_error()
    return value


def encode_cursor(created_at: datetime, run_id: uuid.UUID) -> str:
    payload = json.dumps(
        {
            "createdAt": normalize_utc_datetime(created_at).isoformat(),
            "id": str(run_id),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(value: str | None) -> tuple[datetime | None, uuid.UUID | None]:
    if value is None:
        return None, None
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(value + padding).decode("utf-8")
        )
        if not isinstance(payload, dict):
            raise ValueError
        created_at = normalize_utc_datetime(datetime.fromisoformat(payload["createdAt"]))
        run_id = uuid.UUID(payload["id"])
        return created_at, run_id
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        raise request_invalid_error() from None


def configuration_response() -> HistoricalAnalysisConfigurationResponse:
    return HistoricalAnalysisConfigurationResponse(
        minimum_range_days=MINIMUM_RANGE_DAYS,
        maximum_range_days=MAXIMUM_RANGE_DAYS,
        maximum_active_runs=MAXIMUM_ACTIVE_RUNS,
        simulation_version=SIMULATION_VERSION,
        assumption_version=ASSUMPTION_VERSION,
        assumptions=HistoricalAnalysisAssumptionsResponse(
            signal_timing="confirmed_candle_close",
            entry_timing="next_candle_open",
            holding_period_candles=6,
            fee_bps_per_side="10",
            slippage_bps_per_side="5",
            position_sizing="one_position_full_equity",
            overlapping_signals="ignored",
            end_of_range="incomplete_trade_not_opened",
        ),
    )


historical_analysis_service = HistoricalAnalysisService()
