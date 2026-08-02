import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SignalSubscription(Base):
    __tablename__ = "signal_subscriptions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="ck_signal_subscriptions_status"),
        CheckConstraint("(status = 'active' AND disabled_at IS NULL) OR (status = 'disabled' AND disabled_at IS NOT NULL)", name="ck_signal_subscriptions_lifecycle"),
        UniqueConstraint("user_id", "supported_market_id", "signal_preset_id", name="uq_signal_subscriptions_combination"),
        Index("ix_signal_subscriptions_user_created", "user_id", text("created_at DESC"), text("id DESC")),
        Index("ix_signal_subscriptions_active_preset", "signal_preset_id", "user_id", postgresql_where=text("status = 'active'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    supported_market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supported_markets.id", ondelete="RESTRICT"), nullable=False)
    signal_preset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signal_presets.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_delivery_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), default=False, nullable=False)
    telegram_delivery_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
