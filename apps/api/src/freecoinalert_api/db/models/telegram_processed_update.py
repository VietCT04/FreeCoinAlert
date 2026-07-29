import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class TelegramProcessedUpdate(Base):
    __tablename__ = "telegram_processed_updates"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ("
            "'linked', 'already_linked', 'invalid_token', 'expired_token', "
            "'consumed_token', 'revoked_token', 'ownership_conflict', "
            "'unsupported_update'"
            ")",
            name="ck_telegram_processed_updates_outcome",
        ),
    )

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("telegram_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    confirmation_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    connection: Mapped["TelegramConnection | None"] = relationship(
        back_populates="processed_updates",
    )
