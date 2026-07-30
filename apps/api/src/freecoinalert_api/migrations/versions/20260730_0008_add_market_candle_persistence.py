"""Add canonical and derived market candle persistence.

Revision ID: 20260730_0008
Revises: 20260730_0007
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0008"
down_revision: str | Sequence[str] | None = "20260730_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_candles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("open_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("close_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("status_reason", sa.String(length=64), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("supersedes_candle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_candle_count", sa.Integer(), nullable=False),
        sa.Column("expected_source_candle_count", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("open_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("high_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("low_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("close_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("base_volume", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("quote_volume", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("trade_count", sa.BigInteger(), nullable=True),
        sa.Column("first_trade_id", sa.BigInteger(), nullable=True),
        sa.Column("last_trade_id", sa.BigInteger(), nullable=True),
        sa.Column("provider_event_time", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("provider_close_time", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("received_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "timeframe IN ('1m', '1h', '4h')",
            name="ck_market_candles_timeframe",
        ),
        sa.CheckConstraint(
            "source_kind IN ('binance_kline', 'aggregate_1m')",
            name="ck_market_candles_source_kind",
        ),
        sa.CheckConstraint(
            "status IN ('complete', 'incomplete', 'invalid', 'superseded')",
            name="ck_market_candles_status",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_market_candles_revision_positive"),
        sa.CheckConstraint("close_time > open_time", name="ck_market_candles_time_order"),
        sa.CheckConstraint(
            "close_time = open_time + CASE timeframe "
            "WHEN '1m' THEN INTERVAL '1 minute' "
            "WHEN '1h' THEN INTERVAL '1 hour' "
            "ELSE INTERVAL '4 hours' END",
            name="ck_market_candles_timeframe_duration",
        ),
        sa.CheckConstraint(
            "date_trunc('minute', open_time) = open_time "
            "AND (timeframe = '1m' OR date_part('minute', open_time) = 0) "
            "AND (timeframe <> '4h' OR date_part('hour', open_time)::integer % 4 = 0)",
            name="ck_market_candles_utc_boundary",
        ),
        sa.CheckConstraint(
            "(status = 'superseded' AND is_current = false) "
            "OR (status <> 'superseded' AND is_current = true)",
            name="ck_market_candles_current_status",
        ),
        sa.CheckConstraint(
            "(revision = 1 AND supersedes_candle_id IS NULL) "
            "OR (revision > 1 AND supersedes_candle_id IS NOT NULL)",
            name="ck_market_candles_revision_chain",
        ),
        sa.CheckConstraint(
            "(timeframe = '1m' AND source_kind = 'binance_kline' "
            "AND expected_source_candle_count = 1 AND source_candle_count = 1 "
            "AND source_fingerprint IS NULL) "
            "OR (timeframe IN ('1h', '4h') AND source_kind = 'aggregate_1m' "
            "AND expected_source_candle_count = CASE timeframe WHEN '1h' THEN 60 ELSE 240 END)",
            name="ck_market_candles_source_shape",
        ),
        sa.CheckConstraint(
            "source_candle_count >= 0 AND source_candle_count <= expected_source_candle_count",
            name="ck_market_candles_source_count_range",
        ),
        sa.CheckConstraint(
            "status IN ('incomplete', 'invalid') "
            "OR source_candle_count = expected_source_candle_count",
            name="ck_market_candles_complete_source_count",
        ),
        sa.CheckConstraint(
            "source_kind = 'binance_kline' "
            "OR status IN ('incomplete', 'invalid') "
            "OR source_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_market_candles_derived_fingerprint",
        ),
        sa.CheckConstraint(
            "(status IN ('incomplete', 'invalid') AND status_reason IS NOT NULL "
            "AND open_price IS NULL AND high_price IS NULL AND low_price IS NULL "
            "AND close_price IS NULL AND base_volume IS NULL AND quote_volume IS NULL "
            "AND trade_count IS NULL AND first_trade_id IS NULL AND last_trade_id IS NULL) "
            "OR status IN ('complete', 'superseded')",
            name="ck_market_candles_noncomplete_values",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(
            ["supported_market_id"],
            ["supported_markets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supported_market_id",
            "timeframe",
            "open_time",
            "revision",
            name="uq_market_candles_revision",
        ),
    )
    op.create_index(
        "uq_market_candles_current",
        "market_candles",
        ["supported_market_id", "timeframe", "open_time"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "ix_market_candles_strategy_read",
        "market_candles",
        ["supported_market_id", "timeframe", sa.text("open_time DESC")],
        postgresql_where=sa.text("is_current = true AND status = 'complete'"),
    )
    op.create_index(
        "ix_market_candles_timeframe_open_time",
        "market_candles",
        ["timeframe", "open_time"],
    )
    op.create_foreign_key(
        "fk_market_candles_supersedes_candle_id",
        "market_candles",
        "market_candles",
        ["supersedes_candle_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_index("ix_market_candles_timeframe_open_time", table_name="market_candles")
    op.drop_index("ix_market_candles_strategy_read", table_name="market_candles")
    op.drop_index("uq_market_candles_current", table_name="market_candles")
    op.drop_table("market_candles")
