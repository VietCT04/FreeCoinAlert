import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SignalEventInvalidation(Base):
    __tablename__ = "signal_event_invalidations"
    __table_args__ = (
        CheckConstraint("reason IN ('candle_corrected', 'preset_disabled', 'calculation_invariant')", name="ck_signal_event_invalidations_reason"),
        UniqueConstraint("signal_event_id", name="uq_signal_event_invalidations_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    signal_event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("signal_events.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_candle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("market_candles.id", ondelete="RESTRICT"), nullable=True)
    replacement_candle_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
