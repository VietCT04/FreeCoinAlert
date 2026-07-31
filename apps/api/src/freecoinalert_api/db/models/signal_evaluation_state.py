import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SignalEvaluationState(Base):
    __tablename__ = "signal_evaluation_states"
    __table_args__ = (
        CheckConstraint("status IN ('warming', 'ready', 'stale', 'error', 'disabled')", name="ck_signal_evaluation_states_status"),
        CheckConstraint("last_relation IS NULL OR last_relation IN ('below', 'equal', 'above')", name="ck_signal_evaluation_states_relation"),
        CheckConstraint("calculation_state_version = 1", name="ck_signal_evaluation_states_calculation_version"),
        UniqueConstraint("supported_market_id", "signal_preset_id", name="uq_signal_evaluation_states_market_preset"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    supported_market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supported_markets.id", ondelete="CASCADE"), nullable=False)
    signal_preset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signal_presets.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="warming")
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_candle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("market_candles.id", ondelete="RESTRICT"), nullable=True)
    last_candle_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_candle_open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_relation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_left_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    last_right_value: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    calculation_state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    calculation_state: Mapped[dict[str, str | int]] = mapped_column(JSON, nullable=False, default=dict)
    initialized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
