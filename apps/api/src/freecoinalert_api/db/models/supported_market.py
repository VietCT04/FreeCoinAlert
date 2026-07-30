import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class SupportedMarket(Base):
    __tablename__ = "supported_markets"
    __table_args__ = (
        CheckConstraint("exchange = 'binance'", name="ck_supported_markets_exchange"),
        CheckConstraint("market_type = 'spot'", name="ck_supported_markets_market_type"),
        CheckConstraint(
            "provider_status IN ('pending_metadata', 'trading', 'halt', 'break', "
            "'unsupported', 'metadata_error')",
            name="ck_supported_markets_provider_status",
        ),
        CheckConstraint(
            "min_price IS NULL OR (min_price >= 0 AND min_price <> 'NaN'::numeric "
            "AND min_price <> 'Infinity'::numeric)",
            name="ck_supported_markets_min_price_finite",
        ),
        CheckConstraint(
            "max_price IS NULL OR (max_price >= 0 AND max_price <> 'NaN'::numeric "
            "AND max_price <> 'Infinity'::numeric)",
            name="ck_supported_markets_max_price_finite",
        ),
        CheckConstraint(
            "price_tick IS NULL OR (price_tick >= 0 AND price_tick <> 'NaN'::numeric "
            "AND price_tick <> 'Infinity'::numeric)",
            name="ck_supported_markets_price_tick_finite",
        ),
        CheckConstraint(
            "min_price IS NULL OR max_price IS NULL OR max_price >= min_price",
            name="ck_supported_markets_price_bounds",
        ),
        UniqueConstraint("exchange", "market_type", "symbol", name="uq_supported_markets_symbol"),
        UniqueConstraint(
            "exchange",
            "market_type",
            "stream_symbol",
            name="uq_supported_markets_stream_symbol",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    market_type: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    stream_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    base_asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quote_asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_status: Mapped[str] = mapped_column(String(32), nullable=False)
    product_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    price_tick: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    metadata_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
