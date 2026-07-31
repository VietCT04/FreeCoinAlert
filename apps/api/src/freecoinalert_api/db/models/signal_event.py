import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SignalEvent(Base):
    __tablename__ = "signal_events"
    __table_args__ = (
        CheckConstraint("event_type = 'preset_crossed'", name="ck_signal_events_type"),
        UniqueConstraint("stream_sequence", name="uq_signal_events_stream_sequence"),
        UniqueConstraint("trigger_identity", name="uq_signal_events_trigger_identity"),
        UniqueConstraint("supported_market_id", "signal_preset_id", "trigger_candle_id", "candle_revision", name="uq_signal_events_occurrence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    stream_sequence: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    supported_market_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supported_markets.id", ondelete="RESTRICT"), nullable=False)
    signal_preset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signal_presets.id", ondelete="RESTRICT"), nullable=False)
    trigger_candle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("market_candles.id", ondelete="RESTRICT"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="preset_crossed")
    trigger_identity: Mapped[str] = mapped_column(String(256), nullable=False)
    exchange_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    quote_asset_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    preset_code_snapshot: Mapped[str] = mapped_column(String(96), nullable=False)
    preset_version_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    preset_name_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_type_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    calculation_version_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)
    timeframe_snapshot: Mapped[str] = mapped_column(String(8), nullable=False)
    direction_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    period_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    price_input_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    candle_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    candle_close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_left_value: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    previous_right_value: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    current_left_value: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    current_right_value: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    candle_close_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    backfilled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
