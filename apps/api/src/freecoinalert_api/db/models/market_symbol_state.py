import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class MarketSymbolState(Base):
    __tablename__ = "market_symbol_states"
    __table_args__ = (
        CheckConstraint(
            "status IN ('starting', 'live', 'stale', 'disconnected', 'error')",
            name="ck_market_symbol_states_status",
        ),
        CheckConstraint(
            "last_provider_event_id IS NULL OR last_provider_event_id >= 0",
            name="ck_market_symbol_states_provider_id_nonnegative",
        ),
        CheckConstraint(
            "last_price IS NULL OR (last_price > 0 AND last_price <> 'NaN'::numeric "
            "AND last_price <> 'Infinity'::numeric)",
            name="ck_market_symbol_states_price_finite",
        ),
    )

    supported_market_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supported_markets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_provider_event_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    last_provider_trade_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection_generation: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
