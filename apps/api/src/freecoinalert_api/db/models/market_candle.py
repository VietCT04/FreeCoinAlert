import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        CheckConstraint("timeframe IN ('1m', '1h', '4h')", name="ck_market_candles_timeframe"),
        CheckConstraint(
            "source_kind IN ('binance_kline', 'aggregate_1m')",
            name="ck_market_candles_source_kind",
        ),
        CheckConstraint(
            "status IN ('complete', 'incomplete', 'invalid', 'superseded')",
            name="ck_market_candles_status",
        ),
        CheckConstraint("revision >= 1", name="ck_market_candles_revision_positive"),
        CheckConstraint("close_time > open_time", name="ck_market_candles_time_order"),
        CheckConstraint(
            "close_time = open_time + CASE timeframe "
            "WHEN '1m' THEN INTERVAL '1 minute' "
            "WHEN '1h' THEN INTERVAL '1 hour' "
            "ELSE INTERVAL '4 hours' END",
            name="ck_market_candles_timeframe_duration",
        ),
        CheckConstraint(
            "date_trunc('minute', open_time) = open_time "
            "AND (timeframe = '1m' OR date_part('minute', open_time) = 0) "
            "AND (timeframe <> '4h' OR date_part('hour', open_time)::integer % 4 = 0)",
            name="ck_market_candles_utc_boundary",
        ),
        CheckConstraint(
            "(status = 'superseded' AND is_current = false) "
            "OR (status <> 'superseded' AND is_current = true)",
            name="ck_market_candles_current_status",
        ),
        CheckConstraint(
            "(revision = 1 AND supersedes_candle_id IS NULL) "
            "OR (revision > 1 AND supersedes_candle_id IS NOT NULL)",
            name="ck_market_candles_revision_chain",
        ),
        CheckConstraint(
            "(timeframe = '1m' AND source_kind = 'binance_kline' "
            "AND expected_source_candle_count = 1 AND source_candle_count = 1 "
            "AND source_fingerprint IS NULL) "
            "OR (timeframe IN ('1h', '4h') AND source_kind = 'aggregate_1m' "
            "AND expected_source_candle_count = CASE timeframe WHEN '1h' THEN 60 ELSE 240 END)",
            name="ck_market_candles_source_shape",
        ),
        CheckConstraint(
            "source_candle_count >= 0 AND source_candle_count <= expected_source_candle_count",
            name="ck_market_candles_source_count_range",
        ),
        CheckConstraint(
            "status IN ('incomplete', 'invalid') "
            "OR source_candle_count = expected_source_candle_count",
            name="ck_market_candles_complete_source_count",
        ),
        CheckConstraint(
            "source_kind = 'binance_kline' "
            "OR status IN ('incomplete', 'invalid') "
            "OR source_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_market_candles_derived_fingerprint",
        ),
        CheckConstraint(
            "(status IN ('incomplete', 'invalid') AND status_reason IS NOT NULL "
            "AND open_price IS NULL AND high_price IS NULL AND low_price IS NULL "
            "AND close_price IS NULL AND base_volume IS NULL AND quote_volume IS NULL "
            "AND trade_count IS NULL AND first_trade_id IS NULL AND last_trade_id IS NULL) "
            "OR status IN ('complete', 'superseded')",
            name="ck_market_candles_noncomplete_values",
        ),
        CheckConstraint(
            "(status IN ('complete', 'superseded') AND status_reason IS NULL "
            "AND open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0 "
            "AND base_volume >= 0 AND quote_volume >= 0 AND trade_count >= 0 "
            "AND high_price >= open_price AND high_price >= close_price AND high_price >= low_price "
            "AND low_price <= open_price AND low_price <= close_price "
            "AND open_price <> 'NaN'::numeric AND high_price <> 'NaN'::numeric "
            "AND low_price <> 'NaN'::numeric AND close_price <> 'NaN'::numeric "
            "AND base_volume <> 'NaN'::numeric AND quote_volume <> 'NaN'::numeric "
            "AND open_price <> 'Infinity'::numeric AND high_price <> 'Infinity'::numeric "
            "AND low_price <> 'Infinity'::numeric AND close_price <> 'Infinity'::numeric "
            "AND base_volume <> 'Infinity'::numeric AND quote_volume <> 'Infinity'::numeric) "
            "OR status IN ('incomplete', 'invalid')",
            name="ck_market_candles_complete_values",
        ),
        CheckConstraint(
            "(source_kind = 'binance_kline' AND status IN ('complete', 'superseded') "
            "AND first_trade_id IS NOT NULL AND last_trade_id IS NOT NULL "
            "AND first_trade_id >= 0 AND last_trade_id >= first_trade_id "
            "AND provider_event_time IS NOT NULL AND provider_close_time IS NOT NULL) "
            "OR (source_kind = 'binance_kline' AND status IN ('incomplete', 'invalid')) "
            "OR (source_kind = 'aggregate_1m' AND first_trade_id IS NULL "
            "AND last_trade_id IS NULL AND provider_event_time IS NULL "
            "AND provider_close_time IS NULL)",
            name="ck_market_candles_provider_identity",
        ),
        UniqueConstraint(
            "supported_market_id",
            "timeframe",
            "open_time",
            "revision",
            name="uq_market_candles_revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    supported_market_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supported_markets.id", ondelete="CASCADE"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    supersedes_candle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("market_candles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_source_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    base_volume: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    trade_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    first_trade_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_trade_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    provider_event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
