import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class TelegramConnection(Base):
    __tablename__ = "telegram_connections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('connected', 'degraded', 'disconnected')",
            name="ck_telegram_connections_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
    )
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
    )
    telegram_username: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
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
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    degraded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user: Mapped["User"] = relationship(back_populates="telegram_connection")
    processed_updates: Mapped[list["TelegramProcessedUpdate"]] = relationship(
        back_populates="connection",
        passive_deletes=True,
    )
    notification_outbox_entries: Mapped[list["NotificationOutbox"]] = relationship(
        back_populates="telegram_connection",
        passive_deletes=True,
    )
