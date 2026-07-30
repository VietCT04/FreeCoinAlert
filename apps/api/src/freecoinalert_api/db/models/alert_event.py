import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (
        CheckConstraint("event_type = 'price_crossed'", name="ck_alert_events_event_type"),
        CheckConstraint(
            "direction IN ('cross_above', 'cross_below')",
            name="ck_alert_events_direction",
        ),
        CheckConstraint(
            "trigger_identity ~ '^binance:spot:[A-Z0-9]+:aggTrade:[0-9]+$'",
            name="ck_alert_events_trigger_identity",
        ),
        CheckConstraint(
            "target_price > 0 AND target_price <> 'NaN'::numeric "
            "AND target_price <> 'Infinity'::numeric",
            name="ck_alert_events_target_price_finite",
        ),
        CheckConstraint(
            "trigger_price > 0 AND trigger_price <> 'NaN'::numeric "
            "AND trigger_price <> 'Infinity'::numeric",
            name="ck_alert_events_trigger_price_finite",
        ),
        CheckConstraint("provider_event_id >= 0", name="ck_alert_events_provider_id_nonnegative"),
        UniqueConstraint("alert_id", name="uq_alert_events_alert_id"),
        UniqueConstraint(
            "alert_id",
            "trigger_identity",
            name="uq_alert_events_alert_trigger_identity",
        ),
        Index(
            "ix_alert_events_user_created",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index("ix_alert_events_alert_id", "alert_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("price_alerts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    telegram_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telegram_connections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_identity: Mapped[str] = mapped_column(String(160), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset: Mapped[str] = mapped_column(String(32), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    trigger_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    provider_event_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    provider_event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_after_reconnect: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
