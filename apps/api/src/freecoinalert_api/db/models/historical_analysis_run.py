import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class HistoricalAnalysisRun(Base):
    __tablename__ = "historical_analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_historical_analysis_runs_status",
        ),
        CheckConstraint(
            "analysis_end > analysis_start",
            name="ck_historical_analysis_runs_range",
        ),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_historical_analysis_runs_progress_percent",
        ),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts > 0 AND attempt_count <= max_attempts",
            name="ck_historical_analysis_runs_attempts",
        ),
        CheckConstraint(
            "((status = 'queued' AND started_at IS NULL AND completed_at IS NULL "
            "AND failed_at IS NULL AND cancelled_at IS NULL "
            "AND cancellation_requested_at IS NULL) OR "
            "(status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL "
            "AND failed_at IS NULL AND cancelled_at IS NULL) OR "
            "(status = 'succeeded' AND started_at IS NOT NULL "
            "AND completed_at IS NOT NULL AND failed_at IS NULL "
            "AND cancelled_at IS NULL AND cancellation_requested_at IS NULL) OR "
            "(status = 'failed' AND started_at IS NOT NULL "
            "AND failed_at IS NOT NULL AND completed_at IS NULL "
            "AND cancelled_at IS NULL AND cancellation_requested_at IS NULL) OR "
            "(status = 'cancelled' AND cancelled_at IS NOT NULL AND completed_at IS NULL "
            "AND failed_at IS NULL AND cancellation_requested_at IS NOT NULL))",
            name="ck_historical_analysis_runs_lifecycle",
        ),
        CheckConstraint(
            "((status = 'failed' AND failure_code IS NOT NULL) OR "
            "(status <> 'failed' AND failure_code IS NULL))",
            name="ck_historical_analysis_runs_failure_lifecycle",
        ),
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_historical_analysis_runs_user_idempotency_key",
        ),
        Index(
            "ix_historical_analysis_runs_user_created",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_historical_analysis_runs_queued_available",
            "available_at",
            "created_at",
            postgresql_where=text("status = 'queued'"),
        ),
        Index(
            "ix_historical_analysis_runs_active_user",
            "user_id",
            "created_at",
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
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
    idempotency_key: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    exchange_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    quote_asset_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    preset_code_snapshot: Mapped[str] = mapped_column(String(96), nullable=False)
    preset_version_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    preset_name_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_type_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe_snapshot: Mapped[str] = mapped_column(String(8), nullable=False)
    direction_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    period_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(38, 18),
        nullable=True,
    )
    price_input_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    calculation_version_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    simulation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    assumption_version: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    analysis_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    progress_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        server_default=text("0"),
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        server_default=text("0"),
        nullable=False,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        server_default=text("3"),
        nullable=False,
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
