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


class HistoricalAnalysisDataset(Base):
    __tablename__ = "historical_analysis_datasets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ready', 'stale', 'failed')",
            name="ck_historical_analysis_datasets_status",
        ),
        CheckConstraint(
            "timeframe IN ('1h', '4h')",
            name="ck_historical_analysis_datasets_timeframe",
        ),
        CheckConstraint(
            "failure_code IS NULL OR failure_code IN ("
            "'historical_dataset_insufficient_warmup', "
            "'historical_dataset_gap_detected', "
            "'historical_dataset_incomplete', "
            "'historical_dataset_invalid', "
            "'historical_dataset_correction_race', "
            "'historical_dataset_too_large', "
            "'historical_dataset_unavailable', "
            "'historical_dataset_stale')",
            name="ck_historical_analysis_datasets_failure_code",
        ),
        CheckConstraint(
            "required_warmup_candles >= 0 "
            "AND warmup_candle_count >= 0 "
            "AND analysis_candle_count >= 0 "
            "AND total_candle_count >= 0 "
            "AND total_candle_count <= 2500",
            name="ck_historical_analysis_datasets_counts_nonnegative",
        ),
        CheckConstraint(
            "total_candle_count = warmup_candle_count + analysis_candle_count",
            name="ck_historical_analysis_datasets_count_sum",
        ),
        CheckConstraint(
            "analysis_end > analysis_start",
            name="ck_historical_analysis_datasets_analysis_range",
        ),
        CheckConstraint(
            "warmup_start < analysis_start",
            name="ck_historical_analysis_datasets_warmup_range",
        ),
        CheckConstraint(
            "last_close_time > first_open_time",
            name="ck_historical_analysis_datasets_time_order",
        ),
        CheckConstraint(
            "manifest_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_historical_analysis_datasets_fingerprint",
        ),
        CheckConstraint(
            "((status = 'ready' AND failure_code IS NULL AND stale_at IS NULL) OR "
            "(status = 'failed' AND failure_code IS NOT NULL AND stale_at IS NULL) OR "
            "(status = 'stale' AND failure_code = 'historical_dataset_stale' "
            "AND stale_at IS NOT NULL))",
            name="ck_historical_analysis_datasets_lifecycle",
        ),
        UniqueConstraint("run_id", name="uq_historical_analysis_datasets_run_id"),
        Index(
            "ix_historical_analysis_datasets_status_updated",
            "status",
            "updated_at",
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
    supported_market_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supported_markets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    signal_preset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("signal_presets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    analysis_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    analysis_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    warmup_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    required_warmup_candles: Mapped[int] = mapped_column(Integer, nullable=False)
    warmup_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_close_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    manifest_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    stale_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
