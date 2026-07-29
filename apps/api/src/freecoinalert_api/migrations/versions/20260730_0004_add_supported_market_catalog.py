"""Add supported market catalog.

Revision ID: 20260730_0004
Revises: 20260730_0003
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0004"
down_revision: str | Sequence[str] | None = "20260730_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supported_markets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("market_type", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("stream_symbol", sa.String(length=32), nullable=False),
        sa.Column("base_asset", sa.String(length=32), nullable=True),
        sa.Column("quote_asset", sa.String(length=32), nullable=True),
        sa.Column("provider_status", sa.String(length=32), nullable=False),
        sa.Column("product_enabled", sa.Boolean(), nullable=False),
        sa.Column("min_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("max_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("price_tick", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("metadata_checked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("provider_disabled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status_reason", sa.String(length=64), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("exchange = 'binance'", name="ck_supported_markets_exchange"),
        sa.CheckConstraint("market_type = 'spot'", name="ck_supported_markets_market_type"),
        sa.CheckConstraint("provider_status IN ('pending_metadata', 'trading', 'halt', 'break', 'unsupported', 'metadata_error')", name="ck_supported_markets_provider_status"),
        sa.CheckConstraint("min_price IS NULL OR (min_price >= 0 AND min_price <> 'NaN'::numeric AND min_price <> 'Infinity'::numeric)", name="ck_supported_markets_min_price_finite"),
        sa.CheckConstraint("max_price IS NULL OR (max_price >= 0 AND max_price <> 'NaN'::numeric AND max_price <> 'Infinity'::numeric)", name="ck_supported_markets_max_price_finite"),
        sa.CheckConstraint("price_tick IS NULL OR (price_tick >= 0 AND price_tick <> 'NaN'::numeric AND price_tick <> 'Infinity'::numeric)", name="ck_supported_markets_price_tick_finite"),
        sa.CheckConstraint("min_price IS NULL OR max_price IS NULL OR max_price >= min_price", name="ck_supported_markets_price_bounds"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exchange", "market_type", "symbol", name="uq_supported_markets_symbol"),
        sa.UniqueConstraint("exchange", "market_type", "stream_symbol", name="uq_supported_markets_stream_symbol"),
    )
    supported_markets = sa.table(
        "supported_markets",
        sa.column("exchange", sa.String()),
        sa.column("market_type", sa.String()),
        sa.column("symbol", sa.String()),
        sa.column("stream_symbol", sa.String()),
        sa.column("provider_status", sa.String()),
        sa.column("product_enabled", sa.Boolean()),
    )
    op.bulk_insert(
        supported_markets,
        [
            {"exchange": "binance", "market_type": "spot", "symbol": "BTCUSDT", "stream_symbol": "btcusdt", "provider_status": "pending_metadata", "product_enabled": True},
            {"exchange": "binance", "market_type": "spot", "symbol": "ETHUSDT", "stream_symbol": "ethusdt", "provider_status": "pending_metadata", "product_enabled": True},
            {"exchange": "binance", "market_type": "spot", "symbol": "BNBUSDT", "stream_symbol": "bnbusdt", "provider_status": "pending_metadata", "product_enabled": True},
            {"exchange": "binance", "market_type": "spot", "symbol": "SOLUSDT", "stream_symbol": "solusdt", "provider_status": "pending_metadata", "product_enabled": True},
            {"exchange": "binance", "market_type": "spot", "symbol": "XRPUSDT", "stream_symbol": "xrpusdt", "provider_status": "pending_metadata", "product_enabled": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("supported_markets")
