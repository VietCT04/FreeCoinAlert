import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class TelegramLinkToken(Base):
    __tablename__ = "telegram_link_tokens"
    __table_args__ = (
        CheckConstraint(
            "expires_at > created_at",
            name="ck_telegram_link_tokens_expires_after_created",
        ),
        CheckConstraint(
            "consumed_at IS NULL OR consumed_at >= created_at",
            name="ck_telegram_link_tokens_consumed_after_created",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_telegram_link_tokens_revoked_after_created",
        ),
        CheckConstraint(
            "consumed_at IS NULL OR revoked_at IS NULL",
            name="ck_telegram_link_tokens_not_consumed_and_revoked",
        ),
        Index("ix_telegram_link_tokens_user_id", "user_id"),
        Index("ix_telegram_link_tokens_expires_at", "expires_at"),
        Index(
            "uq_telegram_link_tokens_active_user_id",
            "user_id",
            unique=True,
            postgresql_where=(
                "consumed_at IS NULL AND revoked_at IS NULL"
            ),
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
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    user: Mapped["User"] = relationship(back_populates="telegram_link_tokens")
