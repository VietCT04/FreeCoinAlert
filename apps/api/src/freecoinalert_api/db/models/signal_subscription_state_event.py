import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SignalSubscriptionStateEvent(Base):
    __tablename__ = "signal_subscription_state_events"
    __table_args__ = (
        CheckConstraint(
            "subscription_status IN ('active', 'disabled')",
            name="ck_signal_subscription_state_events_status",
        ),
        Index(
            "ix_signal_subscription_state_events_subscription_effective",
            "subscription_id",
            text("effective_at DESC"),
            text("sequence DESC"),
        ),
        Index(
            "ix_signal_subscription_state_events_market_preset_effective",
            "supported_market_id",
            "signal_preset_id",
            text("effective_at DESC"),
            text("sequence DESC"),
        ),
    )

    sequence: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("signal_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
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
    subscription_status: Mapped[str] = mapped_column(String(32), nullable=False)
    telegram_delivery_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
