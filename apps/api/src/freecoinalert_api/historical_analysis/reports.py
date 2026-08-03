"""Owner-scoped reads for immutable historical-analysis reports and series."""

from __future__ import annotations

import base64
import binascii
import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.historical_analysis_equity_point import (
    HistoricalAnalysisEquityPoint,
)
from freecoinalert_api.db.models.historical_analysis_report import HistoricalAnalysisReport
from freecoinalert_api.db.models.historical_analysis_trade import HistoricalAnalysisTrade
from freecoinalert_api.db.repositories.historical_analysis_reports import (
    get_historical_analysis_report_by_run_id,
    list_historical_analysis_equity_page,
    list_historical_analysis_trades_page,
)
from freecoinalert_api.db.repositories.historical_analysis_runs import (
    get_historical_analysis_run_for_user,
)
from freecoinalert_api.historical_analysis.errors import (
    HistoricalAnalysisError,
    not_found_error,
    report_not_ready_error,
    unavailable_error,
)
from freecoinalert_api.schemas.historical_analysis import (
    HistoricalAnalysisEquityEnvelope,
    HistoricalAnalysisEquityPointResponse,
    HistoricalAnalysisMarketSnapshotResponse,
    HistoricalAnalysisPresetParametersResponse,
    HistoricalAnalysisPresetSnapshotResponse,
    HistoricalAnalysisReportEnvelope,
    HistoricalAnalysisReportResponse,
    HistoricalAnalysisReportSummaryResponse,
    HistoricalAnalysisTradeResponse,
    HistoricalAnalysisTradesEnvelope,
)


DEFAULT_TRADES_LIMIT = 50
MAX_TRADES_LIMIT = 100
DEFAULT_EQUITY_LIMIT = 200
MAX_EQUITY_LIMIT = 500
EQUITY_PREVIEW_LIMIT = 200


class HistoricalAnalysisReportService:
    async def get_report_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> HistoricalAnalysisReportEnvelope:
        try:
            run, report = await self._ready_report(
                session,
                user_id=user_id,
                run_id=run_id,
            )
            points = await list_historical_analysis_equity_page(
                session,
                report_id=report.id,
                limit=2_501,
                after_sequence=None,
            )
            return HistoricalAnalysisReportEnvelope(
                report=_report_response(
                    run_id=run.id,
                    report=report,
                    equity_points=_downsample_equity_points(points),
                )
            )
        except HistoricalAnalysisError:
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def list_trades_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
        limit_value: str | None,
        cursor_value: str | None,
    ) -> HistoricalAnalysisTradesEnvelope:
        try:
            _, report = await self._ready_report(session, user_id=user_id, run_id=run_id)
            limit = parse_series_limit(
                limit_value,
                default=DEFAULT_TRADES_LIMIT,
                maximum=MAX_TRADES_LIMIT,
            )
            after_sequence = decode_sequence_cursor(cursor_value)
            rows = await list_historical_analysis_trades_page(
                session,
                report_id=report.id,
                limit=limit + 1,
                after_sequence=after_sequence,
            )
            page = rows[:limit]
            return HistoricalAnalysisTradesEnvelope(
                trades=[_trade_response(row) for row in page],
                next_cursor=(
                    encode_sequence_cursor(page[-1].sequence)
                    if len(rows) > limit
                    else None
                ),
            )
        except HistoricalAnalysisError:
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def list_equity_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
        limit_value: str | None,
        cursor_value: str | None,
    ) -> HistoricalAnalysisEquityEnvelope:
        try:
            _, report = await self._ready_report(session, user_id=user_id, run_id=run_id)
            limit = parse_series_limit(
                limit_value,
                default=DEFAULT_EQUITY_LIMIT,
                maximum=MAX_EQUITY_LIMIT,
            )
            after_sequence = decode_sequence_cursor(cursor_value)
            rows = await list_historical_analysis_equity_page(
                session,
                report_id=report.id,
                limit=limit + 1,
                after_sequence=after_sequence,
            )
            page = rows[:limit]
            return HistoricalAnalysisEquityEnvelope(
                equity=[_equity_response(row) for row in page],
                next_cursor=(
                    encode_sequence_cursor(page[-1].sequence)
                    if len(rows) > limit
                    else None
                ),
            )
        except HistoricalAnalysisError:
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def _ready_report(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
    ):
        run = await get_historical_analysis_run_for_user(
            session,
            user_id=user_id,
            run_id=run_id,
        )
        if run is None:
            raise not_found_error()
        if run.status != "succeeded":
            raise report_not_ready_error()
        report = await get_historical_analysis_report_by_run_id(
            session,
            run_id=run.id,
        )
        if report is None:
            raise unavailable_error()
        return run, report


historical_analysis_report_service = HistoricalAnalysisReportService()


def parse_series_limit(
    value: str | None,
    *,
    default: int,
    maximum: int,
) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise HistoricalAnalysisError(
            status_code=422,
            code="HISTORICAL_ANALYSIS_REQUEST_INVALID",
            message="The historical-analysis request is invalid.",
        ) from None
    if parsed < 1 or parsed > maximum:
        raise HistoricalAnalysisError(
            status_code=422,
            code="HISTORICAL_ANALYSIS_REQUEST_INVALID",
            message="The historical-analysis request is invalid.",
        )
    return parsed


def encode_sequence_cursor(sequence: int) -> str:
    value = str(sequence).encode("ascii")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def decode_sequence_cursor(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        sequence = int(base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii"))
    except (ValueError, UnicodeError, binascii.Error):
        raise HistoricalAnalysisError(
            status_code=422,
            code="HISTORICAL_ANALYSIS_REQUEST_INVALID",
            message="The historical-analysis request is invalid.",
        ) from None
    if sequence < 0:
        raise HistoricalAnalysisError(
            status_code=422,
            code="HISTORICAL_ANALYSIS_REQUEST_INVALID",
            message="The historical-analysis request is invalid.",
        )
    return sequence


def _report_response(
    *,
    run_id: uuid.UUID,
    report: HistoricalAnalysisReport,
    equity_points: Sequence[HistoricalAnalysisEquityPoint],
) -> HistoricalAnalysisReportResponse:
    market = report.market_snapshot
    preset = report.preset_snapshot
    return HistoricalAnalysisReportResponse(
        report_id=report.id,
        run_id=run_id,
        dataset_id=report.dataset_id,
        market=HistoricalAnalysisMarketSnapshotResponse(
            exchange=str(market["exchange"]),
            market_type=str(market["market_type"]),
            symbol=str(market["symbol"]),
            base_asset=str(market["base_asset"]),
            quote_asset=str(market["quote_asset"]),
        ),
        preset=HistoricalAnalysisPresetSnapshotResponse(
            code=str(preset["code"]),
            version=int(preset["version"]),
            name=str(preset["name"]),
            strategy_type=str(preset["strategy_type"]),
            timeframe=str(preset["timeframe"]),
            direction=str(preset["direction"]),
            parameters=HistoricalAnalysisPresetParametersResponse(
                period=int(preset["period"]),
                threshold=(
                    None if preset.get("threshold") is None else str(preset["threshold"])
                ),
                price_input=str(preset["price_input"]),
            ),
        ),
        calculation_version=report.calculation_version,
        engine_version=report.engine_version,
        assumption_version=report.assumption_version,
        result_fingerprint=report.result_fingerprint,
        dataset_fingerprint=report.dataset_fingerprint,
        analysis_start=report.analysis_start,
        analysis_end=report.analysis_end,
        coverage=_camelize_snapshot(report.coverage_snapshot),
        assumptions=_camelize_snapshot(report.assumptions_snapshot),
        summary=HistoricalAnalysisReportSummaryResponse(
            analysis_candle_count=report.analysis_candle_count,
            signal_count=report.signal_count,
            trade_count=report.trade_count,
            winning_trade_count=report.winning_trade_count,
            losing_trade_count=report.losing_trade_count,
            flat_trade_count=report.flat_trade_count,
            overlapping_signal_count=report.overlapping_signal_count,
            insufficient_forward_signal_count=report.insufficient_forward_signal_count,
            equity_exhausted_signal_count=report.equity_exhausted_signal_count,
            initial_equity=_decimal(report.initial_equity),
            final_equity=_decimal(report.final_equity),
            gross_return=_decimal(report.gross_return),
            net_return=_decimal(report.net_return),
            maximum_drawdown=_decimal(report.maximum_drawdown),
            win_rate=(None if report.win_rate is None else _decimal(report.win_rate)),
            win_rate_undefined_reason=report.win_rate_undefined_reason,
            profit_factor=(
                None if report.profit_factor is None else _decimal(report.profit_factor)
            ),
            profit_factor_undefined_reason=report.profit_factor_undefined_reason,
        ),
        safety_disclosures=list(_safety_disclosures(report.assumptions_snapshot)),
        equity_preview=[_equity_response(point) for point in equity_points],
        trades_available=True,
        equity_available=True,
        trades_path=f"/historical-analyses/{run_id}/trades",
        equity_path=f"/historical-analyses/{run_id}/equity",
    )


def _trade_response(row: HistoricalAnalysisTrade) -> HistoricalAnalysisTradeResponse:
    return HistoricalAnalysisTradeResponse(
        sequence=row.sequence,
        signal_candle_id=row.signal_candle_id,
        signal_candle_revision=row.signal_candle_revision,
        signal_open_time=row.signal_open_time,
        signal_close_time=row.signal_close_time,
        signal_direction=row.signal_direction,
        position_direction=row.position_direction,
        entry_candle_id=row.entry_candle_id,
        entry_candle_revision=row.entry_candle_revision,
        entry_open_time=row.entry_open_time,
        entry_raw_price=_decimal(row.entry_raw_price),
        entry_fill_price=_decimal(row.entry_fill_price),
        exit_candle_id=row.exit_candle_id,
        exit_candle_revision=row.exit_candle_revision,
        exit_close_time=row.exit_close_time,
        exit_raw_price=_decimal(row.exit_raw_price),
        exit_fill_price=_decimal(row.exit_fill_price),
        holding_candle_count=row.holding_candle_count,
        fee_rate=_decimal(row.fee_rate),
        slippage_rate=_decimal(row.slippage_rate),
        equity_before=_decimal(row.equity_before),
        gross_return=_decimal(row.gross_return),
        net_return=_decimal(row.net_return),
        gross_pnl=_decimal(row.gross_pnl),
        net_pnl=_decimal(row.net_pnl),
        equity_after=_decimal(row.equity_after),
        outcome=row.outcome,
    )


def _equity_response(row: HistoricalAnalysisEquityPoint) -> HistoricalAnalysisEquityPointResponse:
    return HistoricalAnalysisEquityPointResponse(
        sequence=row.sequence,
        candle_id=row.candle_id,
        candle_revision=row.candle_revision,
        candle_open_time=row.open_time,
        candle_close_time=row.close_time,
        equity=_decimal(row.equity),
        drawdown=_decimal(row.drawdown),
        position_state=row.position_state,
        active_trade_sequence=row.active_trade_sequence,
    )


def _downsample_equity_points(
    points: Sequence[HistoricalAnalysisEquityPoint],
) -> Sequence[HistoricalAnalysisEquityPoint]:
    if len(points) <= EQUITY_PREVIEW_LIMIT:
        return points
    last_index = len(points) - 1
    return tuple(
        points[(slot * last_index) // (EQUITY_PREVIEW_LIMIT - 1)]
        for slot in range(EQUITY_PREVIEW_LIMIT)
    )


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _safety_disclosures(snapshot: dict[str, object]) -> Sequence[str]:
    value = snapshot.get("safety_disclosures")
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return (
        "historical hypothetical simulation",
        "not financial advice",
        "not a prediction",
        "not a delivery or profit guarantee",
        "synthetic short results are not executable Binance Spot trades",
    )


def _camelize_snapshot(value: dict[str, Any]) -> dict[str, Any]:
    return {
        _to_camel_case(key): _camelize_value(item)
        for key, item in value.items()
    }


def _camelize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _camelize_snapshot(value)
    if isinstance(value, list):
        return [_camelize_value(item) for item in value]
    return value


def _to_camel_case(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])
