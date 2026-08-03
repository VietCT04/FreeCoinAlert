import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.historical_analysis_equity_point import (
    HistoricalAnalysisEquityPoint,
)
from freecoinalert_api.db.models.historical_analysis_report import HistoricalAnalysisReport
from freecoinalert_api.db.models.historical_analysis_trade import HistoricalAnalysisTrade


async def get_historical_analysis_report_by_run_id(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    for_update: bool = False,
) -> HistoricalAnalysisReport | None:
    statement = select(HistoricalAnalysisReport).where(
        HistoricalAnalysisReport.run_id == run_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def list_historical_analysis_trades_page(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    limit: int,
    after_sequence: int | None,
) -> Sequence[HistoricalAnalysisTrade]:
    statement = select(HistoricalAnalysisTrade).where(
        HistoricalAnalysisTrade.report_id == report_id,
    )
    if after_sequence is not None:
        statement = statement.where(HistoricalAnalysisTrade.sequence > after_sequence)
    statement = statement.order_by(HistoricalAnalysisTrade.sequence.asc()).limit(limit)
    return (await session.scalars(statement)).all()


async def list_historical_analysis_equity_page(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    limit: int,
    after_sequence: int | None,
) -> Sequence[HistoricalAnalysisEquityPoint]:
    statement = select(HistoricalAnalysisEquityPoint).where(
        HistoricalAnalysisEquityPoint.report_id == report_id,
    )
    if after_sequence is not None:
        statement = statement.where(HistoricalAnalysisEquityPoint.sequence > after_sequence)
    statement = statement.order_by(HistoricalAnalysisEquityPoint.sequence.asc()).limit(limit)
    return (await session.scalars(statement)).all()


async def create_historical_analysis_report(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    user_id: uuid.UUID,
    dataset_id: uuid.UUID,
    result_fingerprint: str,
    dataset_fingerprint: str,
    engine_version: str,
    assumption_version: str,
    calculation_version: str,
    market_snapshot: dict[str, object],
    preset_snapshot: dict[str, object],
    coverage_snapshot: dict[str, object],
    assumptions_snapshot: dict[str, object],
    analysis_start: datetime,
    analysis_end: datetime,
    analysis_candle_count: int,
    signal_count: int,
    trade_count: int,
    winning_trade_count: int,
    losing_trade_count: int,
    flat_trade_count: int,
    overlapping_signal_count: int,
    insufficient_forward_signal_count: int,
    equity_exhausted_signal_count: int,
    initial_equity: Decimal,
    final_equity: Decimal,
    gross_return: Decimal,
    net_return: Decimal,
    maximum_drawdown: Decimal,
    win_rate: Decimal | None,
    win_rate_undefined_reason: str | None,
    profit_factor: Decimal | None,
    profit_factor_undefined_reason: str | None,
) -> HistoricalAnalysisReport:
    report = HistoricalAnalysisReport(
        run_id=run_id,
        user_id=user_id,
        dataset_id=dataset_id,
        result_fingerprint=result_fingerprint,
        dataset_fingerprint=dataset_fingerprint,
        engine_version=engine_version,
        assumption_version=assumption_version,
        calculation_version=calculation_version,
        market_snapshot=market_snapshot,
        preset_snapshot=preset_snapshot,
        coverage_snapshot=coverage_snapshot,
        assumptions_snapshot=assumptions_snapshot,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        analysis_candle_count=analysis_candle_count,
        signal_count=signal_count,
        trade_count=trade_count,
        winning_trade_count=winning_trade_count,
        losing_trade_count=losing_trade_count,
        flat_trade_count=flat_trade_count,
        overlapping_signal_count=overlapping_signal_count,
        insufficient_forward_signal_count=insufficient_forward_signal_count,
        equity_exhausted_signal_count=equity_exhausted_signal_count,
        initial_equity=initial_equity,
        final_equity=final_equity,
        gross_return=gross_return,
        net_return=net_return,
        maximum_drawdown=maximum_drawdown,
        win_rate=win_rate,
        win_rate_undefined_reason=win_rate_undefined_reason,
        profit_factor=profit_factor,
        profit_factor_undefined_reason=profit_factor_undefined_reason,
    )
    session.add(report)
    await session.flush()
    return report


async def create_historical_analysis_trades(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    trades: Sequence[dict[str, object]],
) -> None:
    session.add_all(
        HistoricalAnalysisTrade(report_id=report_id, **trade)
        for trade in trades
    )
    await session.flush()


async def create_historical_analysis_equity_points(
    session: AsyncSession,
    *,
    report_id: uuid.UUID,
    points: Sequence[dict[str, object]],
) -> None:
    session.add_all(
        HistoricalAnalysisEquityPoint(report_id=report_id, **point)
        for point in points
    )
    await session.flush()
