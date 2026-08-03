import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class HistoricalAnalysisEquityPoint(Base):
    __tablename__ = "historical_analysis_equity_points"
    __table_args__ = (
        CheckConstraint("sequence >= 0", name="ck_historical_analysis_equity_points_sequence"),
        CheckConstraint("candle_revision >= 1", name="ck_historical_analysis_equity_points_revision"),
        CheckConstraint(
            "close_time > open_time",
            name="ck_historical_analysis_equity_points_time_order",
        ),
        CheckConstraint(
            "equity >= 0 AND drawdown >= -1 AND drawdown <= 0",
            name="ck_historical_analysis_equity_points_values",
        ),
        CheckConstraint(
            "position_state IN ('flat', 'long', 'synthetic_short')",
            name="ck_historical_analysis_equity_points_position_state",
        ),
        CheckConstraint(
            "active_trade_sequence IS NULL OR active_trade_sequence >= 1",
            name="ck_historical_analysis_equity_points_active_trade",
        ),
        UniqueConstraint(
            "report_id",
            "sequence",
            name="uq_historical_analysis_equity_points_report_sequence",
        ),
        Index(
            "ix_historical_analysis_equity_points_report_sequence",
            "report_id",
            "sequence",
        ),
        Index(
            "ix_historical_analysis_equity_points_candle_id",
            "candle_id",
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
    candle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("market_candles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candle_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    position_state: Mapped[str] = mapped_column(String(32), nullable=False)
    active_trade_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
