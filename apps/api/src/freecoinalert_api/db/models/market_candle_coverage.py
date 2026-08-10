import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class MarketCandleCoverage(Base):
    """Derived canonical coverage state; market_candles remains authoritative."""

    __tablename__ = "market_candle_coverage"
    __table_args__ = (
        CheckConstraint("exchange = 'binance'", name="ck_market_candle_coverage_exchange"),
        CheckConstraint("market_type = 'spot'", name="ck_market_candle_coverage_market_type"),
        CheckConstraint(
            "timeframe IN ('1m', '1h', '4h')",
            name="ck_market_candle_coverage_timeframe",
        ),
        CheckConstraint(
            "status IN ('backfilling', 'ready', 'degraded')",
            name="ck_market_candle_coverage_status",
        ),
        CheckConstraint(
            "target_end > target_start",
            name="ck_market_candle_coverage_target_range",
        ),
        CheckConstraint(
            "latest_closed_boundary >= target_end",
            name="ck_market_candle_coverage_latest_boundary",
        ),
        CheckConstraint(
            "missing_range_count >= 0",
            name="ck_market_candle_coverage_missing_count",
        ),
        CheckConstraint(
            "coverage_percent >= 0 AND coverage_percent <= 100",
            name="ck_market_candle_coverage_percent",
        ),
        CheckConstraint(
            "(contiguous_start IS NULL AND contiguous_end IS NULL) "
            "OR (contiguous_start IS NOT NULL AND contiguous_end IS NOT NULL "
            "AND contiguous_end > contiguous_start)",
            name="ck_market_candle_coverage_contiguous_range",
        ),
        CheckConstraint(
            "(available_start IS NULL AND available_end IS NULL) "
            "OR (available_start IS NOT NULL AND available_end IS NOT NULL "
            "AND available_end > available_start)",
            name="ck_market_candle_coverage_available_range",
        ),
        UniqueConstraint(
            "supported_market_id",
            "timeframe",
            name="uq_market_candle_coverage_market_timeframe",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    supported_market_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supported_markets.id", ondelete="CASCADE"),
        nullable=False,
    )
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    target_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_closed_boundary: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    contiguous_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    contiguous_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    available_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    available_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    missing_range_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_percent: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
