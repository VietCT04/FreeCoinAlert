import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class HistoricalAnalysisReport(Base):
    __tablename__ = "historical_analysis_reports"
    __table_args__ = (
        CheckConstraint(
            "result_fingerprint ~ '^[0-9a-f]{64}$' AND dataset_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_historical_analysis_reports_fingerprints",
        ),
        CheckConstraint(
            "analysis_end > analysis_start",
            name="ck_historical_analysis_reports_range",
        ),
        CheckConstraint(
            "analysis_candle_count >= 0 AND signal_count >= 0 AND trade_count >= 0 "
            "AND winning_trade_count >= 0 AND losing_trade_count >= 0 AND flat_trade_count >= 0 "
            "AND overlapping_signal_count >= 0 AND insufficient_forward_signal_count >= 0 "
            "AND equity_exhausted_signal_count >= 0",
            name="ck_historical_analysis_reports_counts_nonnegative",
        ),
        CheckConstraint(
            "initial_equity >= 0 AND final_equity >= 0",
            name="ck_historical_analysis_reports_equity_nonnegative",
        ),
        CheckConstraint(
            "((win_rate IS NULL AND win_rate_undefined_reason IS NOT NULL) OR "
            "(win_rate IS NOT NULL AND win_rate_undefined_reason IS NULL "
            "AND win_rate >= 0 AND win_rate <= 1))",
            name="ck_historical_analysis_reports_win_rate",
        ),
        CheckConstraint(
            "((profit_factor IS NULL AND profit_factor_undefined_reason IS NOT NULL) OR "
            "(profit_factor IS NOT NULL AND profit_factor_undefined_reason IS NULL "
            "AND profit_factor >= 0))",
            name="ck_historical_analysis_reports_profit_factor",
        ),
        UniqueConstraint("run_id", name="uq_historical_analysis_reports_run_id"),
        UniqueConstraint("dataset_id", name="uq_historical_analysis_reports_dataset_id"),
        Index(
            "ix_historical_analysis_reports_user_created",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("historical_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("historical_analysis_datasets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    result_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    assumption_version: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    market_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preset_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    coverage_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    assumptions_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    analysis_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analysis_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analysis_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    winning_trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    losing_trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    flat_trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    overlapping_signal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    insufficient_forward_signal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    equity_exhausted_signal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_equity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    final_equity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    gross_return: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    net_return: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    maximum_drawdown: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    win_rate_undefined_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profit_factor: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    profit_factor_undefined_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
