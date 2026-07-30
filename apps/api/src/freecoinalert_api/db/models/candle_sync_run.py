import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class CandleSyncRun(Base):
    __tablename__ = "candle_sync_runs"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('bootstrap', 'reconciliation', 'recent_reconciliation', 'retention_cleanup')",
            name="ck_candle_sync_runs_kind",
        ),
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'cancelled')",
            name="ck_candle_sync_runs_status",
        ),
        CheckConstraint("requested_end > requested_start", name="ck_candle_sync_runs_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_market_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("supported_markets.id", ondelete="SET NULL"), nullable=True
    )
    next_open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_rows_written: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    source_rows_unchanged: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    source_rows_corrected: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    derived_rows_written: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    unresolved_gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
