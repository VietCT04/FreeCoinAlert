import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class CandleSymbolState(Base):
    __tablename__ = "candle_symbol_states"
    __table_args__ = (
        CheckConstraint(
            "status IN ('starting', 'live', 'stale', 'gapped', 'error')",
            name="ck_candle_symbol_states_status",
        ),
        CheckConstraint("unresolved_gap_count >= 0", name="ck_candle_symbol_states_gap_count"),
    )

    supported_market_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supported_markets.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    latest_complete_1m_open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_complete_1h_open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_complete_4h_open_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_websocket_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reconciled_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unresolved_gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status_reason: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
