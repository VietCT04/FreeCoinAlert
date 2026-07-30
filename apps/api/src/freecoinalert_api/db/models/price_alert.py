import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
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


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    __table_args__ = (
        CheckConstraint("kind = 'price_cross'", name="ck_price_alerts_kind"),
        CheckConstraint(
            "direction IN ('cross_above', 'cross_below')",
            name="ck_price_alerts_direction",
        ),
        CheckConstraint(
            "status IN ('active', 'triggered', 'disabled', 'deleted', 'failed')",
            name="ck_price_alerts_status",
        ),
        CheckConstraint(
            "last_relation IS NULL OR last_relation IN ('below', 'equal', 'above')",
            name="ck_price_alerts_last_relation",
        ),
        CheckConstraint(
            "target_price > 0 AND target_price <> 'NaN'::numeric "
            "AND target_price <> 'Infinity'::numeric",
            name="ck_price_alerts_target_price_finite",
        ),
        CheckConstraint(
            "price_tick_snapshot > 0 AND price_tick_snapshot <> 'NaN'::numeric "
            "AND price_tick_snapshot <> 'Infinity'::numeric",
            name="ck_price_alerts_price_tick_snapshot_finite",
        ),
        CheckConstraint(
            "(target_price % price_tick_snapshot) = 0",
            name="ck_price_alerts_target_price_tick",
        ),
        CheckConstraint(
            "last_evaluated_provider_id IS NULL OR last_evaluated_provider_id >= 0",
            name="ck_price_alerts_provider_id_nonnegative",
        ),
        CheckConstraint(
            "last_evaluated_price IS NULL OR (last_evaluated_price > 0 "
            "AND last_evaluated_price <> 'NaN'::numeric "
            "AND last_evaluated_price <> 'Infinity'::numeric)",
            name="ck_price_alerts_evaluated_price_finite",
        ),
        CheckConstraint(
            "(last_relation IS NULL AND last_evaluated_price IS NULL "
            "AND last_evaluated_provider_id IS NULL "
            "AND last_evaluated_provider_time IS NULL) OR "
            "(last_relation IS NOT NULL AND last_evaluated_price IS NOT NULL "
            "AND last_evaluated_provider_id IS NOT NULL "
            "AND last_evaluated_provider_time IS NOT NULL)",
            name="ck_price_alerts_evaluation_state",
        ),
        CheckConstraint(
            "(status = 'active' AND triggered_at IS NULL AND disabled_at IS NULL "
            "AND deleted_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'triggered' AND triggered_at IS NOT NULL AND disabled_at IS NULL "
            "AND deleted_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'disabled' AND triggered_at IS NULL AND disabled_at IS NOT NULL "
            "AND deleted_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'deleted' AND triggered_at IS NULL AND disabled_at IS NULL "
            "AND deleted_at IS NOT NULL AND failed_at IS NULL) OR "
            "(status = 'failed' AND triggered_at IS NULL AND disabled_at IS NULL "
            "AND deleted_at IS NULL AND failed_at IS NOT NULL)",
            name="ck_price_alerts_lifecycle_timestamps",
        ),
        UniqueConstraint(
            "user_id",
            "creation_idempotency_key",
            name="uq_price_alerts_user_creation_idempotency_key",
        ),
        Index(
            "ix_price_alerts_user_created",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index("ix_price_alerts_market_status", "supported_market_id", "status"),
        Index("ix_price_alerts_connection_status", "telegram_connection_id", "status"),
        Index(
            "ix_price_alerts_active_market",
            "supported_market_id",
            "id",
            postgresql_where=text("status = 'active'"),
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
    telegram_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telegram_connections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    creation_idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    target_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    exchange_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    quote_asset_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    price_tick_snapshot: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_relation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_evaluated_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    last_evaluated_provider_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_evaluated_provider_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
