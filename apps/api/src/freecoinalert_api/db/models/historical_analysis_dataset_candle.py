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
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from freecoinalert_api.db.base import Base


class HistoricalAnalysisDatasetCandle(Base):
    __tablename__ = "historical_analysis_dataset_candles"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_historical_analysis_dataset_candles_position"),
        CheckConstraint(
            "candle_revision >= 1",
            name="ck_historical_analysis_dataset_candles_revision",
        ),
        CheckConstraint(
            "timeframe IN ('1h', '4h')",
            name="ck_historical_analysis_dataset_candles_timeframe",
        ),
        CheckConstraint(
            "source_kind = 'aggregate_1m'",
            name="ck_historical_analysis_dataset_candles_source_kind",
        ),
        CheckConstraint(
            "close_time > open_time",
            name="ck_historical_analysis_dataset_candles_time_order",
        ),
        CheckConstraint(
            "close_time = open_time + CASE timeframe "
            "WHEN '1h' THEN INTERVAL '1 hour' "
            "ELSE INTERVAL '4 hours' END",
            name="ck_historical_analysis_dataset_candles_timeframe_duration",
        ),
        CheckConstraint(
            "date_trunc('hour', open_time) = open_time "
            "AND (timeframe <> '4h' OR date_part('hour', open_time)::integer % 4 = 0)",
            name="ck_historical_analysis_dataset_candles_utc_boundary",
        ),
        CheckConstraint(
            "source_candle_count = expected_source_candle_count "
            "AND expected_source_candle_count = CASE timeframe "
            "WHEN '1h' THEN 60 ELSE 240 END",
            name="ck_historical_analysis_dataset_candles_source_counts",
        ),
        CheckConstraint(
            "source_fingerprint IS NULL OR source_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_historical_analysis_dataset_candles_source_fingerprint",
        ),
        CheckConstraint(
            "open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0 "
            "AND base_volume >= 0 AND quote_volume >= 0 AND trade_count >= 0 "
            "AND high_price >= open_price AND high_price >= close_price "
            "AND high_price >= low_price AND low_price <= open_price "
            "AND low_price <= close_price "
            "AND open_price <> 'NaN'::numeric AND high_price <> 'NaN'::numeric "
            "AND low_price <> 'NaN'::numeric AND close_price <> 'NaN'::numeric "
            "AND base_volume <> 'NaN'::numeric AND quote_volume <> 'NaN'::numeric "
            "AND open_price <> 'Infinity'::numeric "
            "AND high_price <> 'Infinity'::numeric "
            "AND low_price <> 'Infinity'::numeric "
            "AND close_price <> 'Infinity'::numeric "
            "AND base_volume <> 'Infinity'::numeric "
            "AND quote_volume <> 'Infinity'::numeric",
            name="ck_historical_analysis_dataset_candles_values",
        ),
        UniqueConstraint(
            "dataset_id",
            "position",
            name="uq_historical_analysis_dataset_candles_position",
        ),
        UniqueConstraint(
            "dataset_id",
            "candle_id",
            name="uq_historical_analysis_dataset_candles_candle",
        ),
        Index(
            "ix_historical_analysis_dataset_candles_dataset_open_time",
            "dataset_id",
            "open_time",
        ),
        Index(
            "ix_historical_analysis_dataset_candles_candle_dataset",
            "candle_id",
            "dataset_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("historical_analysis_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    candle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("market_candles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candle_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    is_warmup: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    close_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    open_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    base_volume: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    quote_volume: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    trade_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_source_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
