import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class CandleBackfillCheckpoint(Base):
    __tablename__ = "candle_backfill_checkpoints"
    __table_args__ = (
        CheckConstraint("exchange = 'binance'", name="ck_candle_backfill_exchange"),
        CheckConstraint("market_type = 'spot'", name="ck_candle_backfill_market_type"),
        CheckConstraint("timeframe = '1m'", name="ck_candle_backfill_timeframe"),
        CheckConstraint(
            "archive_granularity IN ('monthly', 'daily')",
            name="ck_candle_backfill_granularity",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'complete', 'failed')",
            name="ck_candle_backfill_status",
        ),
        CheckConstraint("period_end > period_start", name="ck_candle_backfill_period"),
        CheckConstraint(
            "next_open_time >= period_start AND next_open_time <= period_end",
            name="ck_candle_backfill_next_open_time",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_candle_backfill_attempt_count"),
        CheckConstraint(
            "checksum_sha256 IS NULL OR checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_candle_backfill_checksum",
        ),
        UniqueConstraint("archive_key", name="uq_candle_backfill_archive_key"),
        Index("ix_candle_backfill_status_next_open_time", "status", "next_open_time"),
        Index(
            "ix_candle_backfill_market_period",
            "supported_market_id",
            "period_start",
            "period_end",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    supported_market_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supported_markets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    archive_granularity: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    archive_key: Mapped[str] = mapped_column(String(256), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    next_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
