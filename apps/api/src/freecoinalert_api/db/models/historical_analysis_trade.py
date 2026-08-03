import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class HistoricalAnalysisTrade(Base):
    __tablename__ = "historical_analysis_trades"
    __table_args__ = (
        CheckConstraint("sequence >= 1", name="ck_historical_analysis_trades_sequence"),
        CheckConstraint(
            "signal_candle_revision >= 1 AND entry_candle_revision >= 1 AND exit_candle_revision >= 1",
            name="ck_historical_analysis_trades_revisions",
        ),
        CheckConstraint(
            "signal_direction IN ('cross_above', 'cross_below')",
            name="ck_historical_analysis_trades_signal_direction",
        ),
        CheckConstraint(
            "position_direction IN ('long', 'synthetic_short')",
            name="ck_historical_analysis_trades_position_direction",
        ),
        CheckConstraint(
            "outcome IN ('win', 'loss', 'flat')",
            name="ck_historical_analysis_trades_outcome",
        ),
        CheckConstraint(
            "entry_raw_price > 0 AND entry_fill_price > 0 AND exit_raw_price > 0 AND exit_fill_price > 0",
            name="ck_historical_analysis_trades_prices_positive",
        ),
        CheckConstraint(
            "holding_candle_count > 0 AND fee_rate >= 0 AND slippage_rate >= 0",
            name="ck_historical_analysis_trades_execution_values",
        ),
        CheckConstraint(
            "equity_before >= 0 AND equity_after >= 0",
            name="ck_historical_analysis_trades_equity_nonnegative",
        ),
        UniqueConstraint(
            "report_id",
            "sequence",
            name="uq_historical_analysis_trades_report_sequence",
        ),
        Index(
            "ix_historical_analysis_trades_report_sequence",
            "report_id",
            "sequence",
        ),
        Index(
            "ix_historical_analysis_trades_candle_id",
            "signal_candle_id",
            "entry_candle_id",
            "exit_candle_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("historical_analysis_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_candle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("market_candles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    signal_candle_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    signal_direction: Mapped[str] = mapped_column(String(32), nullable=False)
    position_direction: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_candle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("market_candles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entry_candle_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_raw_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    entry_fill_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    exit_candle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("market_candles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    exit_candle_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    exit_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_raw_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    exit_fill_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    holding_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_rate: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    slippage_rate: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    equity_before: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    gross_return: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    net_return: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    gross_pnl: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    equity_after: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
