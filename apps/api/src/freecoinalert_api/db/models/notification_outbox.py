import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        CheckConstraint("kind = 'telegram_test'", name="ck_notification_outbox_kind"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'retry_wait', 'sent', 'failed')",
            name="ck_notification_outbox_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_notification_outbox_attempt_count"),
        CheckConstraint("max_attempts > 0", name="ck_notification_outbox_max_attempts"),
        CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_notification_outbox_attempt_count_maximum",
        ),
        CheckConstraint(
            "status != 'sent' OR sent_at IS NOT NULL",
            name="ck_notification_outbox_sent_at",
        ),
        CheckConstraint(
            "status != 'failed' OR failed_at IS NOT NULL",
            name="ck_notification_outbox_failed_at",
        ),
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_notification_outbox_user_idempotency_key",
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
    telegram_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telegram_connections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    message_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, server_default=text("5"), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user: Mapped["User"] = relationship(back_populates="notification_outbox_entries")
    telegram_connection: Mapped["TelegramConnection"] = relationship(
        back_populates="notification_outbox_entries"
    )
