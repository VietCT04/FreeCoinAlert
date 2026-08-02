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


class SignalTelegramDispatch(Base):
    __tablename__ = "signal_telegram_dispatches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'retry_wait', 'completed', 'skipped', 'failed')",
            name="ck_signal_telegram_dispatches_status",
        ),
        CheckConstraint(
            "notification_count >= 0",
            name="ck_signal_telegram_dispatches_notification_count",
        ),
        CheckConstraint(
            "skipped_count >= 0",
            name="ck_signal_telegram_dispatches_skipped_count",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_signal_telegram_dispatches_attempt_count",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_signal_telegram_dispatches_max_attempts",
        ),
        CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_signal_telegram_dispatches_attempt_count_maximum",
        ),
        UniqueConstraint(
            "signal_event_id",
            name="uq_signal_telegram_dispatches_signal_event",
        ),
        Index(
            "ix_signal_telegram_dispatches_claim",
            "status",
            "available_at",
            "created_at",
        ),
        Index(
            "ix_signal_telegram_dispatches_processing",
            "status",
            "locked_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    signal_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("signal_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_subscription_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    notification_count: Mapped[int] = mapped_column(
        Integer,
        server_default=text("0"),
        nullable=False,
    )
    skipped_count: Mapped[int] = mapped_column(
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
        server_default=text("10"),
        nullable=False,
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
