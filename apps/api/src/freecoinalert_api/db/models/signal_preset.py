import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SignalPreset(Base):
    __tablename__ = "signal_presets"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_signal_presets_version"),
        CheckConstraint("strategy_type IN ('price_sma_cross', 'rsi_threshold_cross')", name="ck_signal_presets_strategy_type"),
        CheckConstraint("timeframe IN ('1h', '4h')", name="ck_signal_presets_timeframe"),
        CheckConstraint("direction IN ('cross_above', 'cross_below')", name="ck_signal_presets_direction"),
        CheckConstraint("price_input = 'close'", name="ck_signal_presets_price_input"),
        CheckConstraint("status IN ('active', 'superseded', 'disabled')", name="ck_signal_presets_status"),
        CheckConstraint("period > 0", name="ck_signal_presets_period"),
        CheckConstraint("(strategy_type = 'price_sma_cross' AND period = 200 AND threshold IS NULL) OR (strategy_type = 'rsi_threshold_cross' AND period = 14 AND threshold = CASE WHEN direction = 'cross_above' THEN 70 ELSE 30 END)", name="ck_signal_presets_configuration"),
        CheckConstraint("(status = 'active' AND superseded_at IS NULL AND disabled_at IS NULL) OR (status = 'superseded' AND superseded_at IS NOT NULL AND disabled_at IS NULL) OR (status = 'disabled' AND disabled_at IS NOT NULL)", name="ck_signal_presets_lifecycle"),
        UniqueConstraint("code", "version", name="uq_signal_presets_code_version"),
        UniqueConstraint("configuration_hash", name="uq_signal_presets_configuration_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(96), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    period: Mapped[int] = mapped_column(nullable=False)
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    price_input: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
