"""Persist derived canonical candle coverage state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260810_0025"
down_revision: str | Sequence[str] | None = "20260810_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_candle_coverage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("market_type", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("target_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_closed_boundary", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contiguous_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contiguous_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("missing_range_count", sa.Integer(), nullable=False),
        sa.Column("coverage_percent", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_category", sa.String(length=64), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "exchange = 'binance'",
            name="ck_market_candle_coverage_exchange",
        ),
        sa.CheckConstraint(
            "market_type = 'spot'",
            name="ck_market_candle_coverage_market_type",
        ),
        sa.CheckConstraint(
            "timeframe IN ('1m', '1h', '4h')",
            name="ck_market_candle_coverage_timeframe",
        ),
        sa.CheckConstraint(
            "status IN ('backfilling', 'ready', 'degraded')",
            name="ck_market_candle_coverage_status",
        ),
        sa.CheckConstraint(
            "target_end > target_start",
            name="ck_market_candle_coverage_target_range",
        ),
        sa.CheckConstraint(
            "latest_closed_boundary >= target_end",
            name="ck_market_candle_coverage_latest_boundary",
        ),
        sa.CheckConstraint(
            "missing_range_count >= 0",
            name="ck_market_candle_coverage_missing_count",
        ),
        sa.CheckConstraint(
            "coverage_percent >= 0 AND coverage_percent <= 100",
            name="ck_market_candle_coverage_percent",
        ),
        sa.CheckConstraint(
            "(contiguous_start IS NULL AND contiguous_end IS NULL) "
            "OR (contiguous_start IS NOT NULL AND contiguous_end IS NOT NULL "
            "AND contiguous_end > contiguous_start)",
            name="ck_market_candle_coverage_contiguous_range",
        ),
        sa.CheckConstraint(
            "(available_start IS NULL AND available_end IS NULL) "
            "OR (available_start IS NOT NULL AND available_end IS NOT NULL "
            "AND available_end > available_start)",
            name="ck_market_candle_coverage_available_range",
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
            name="uq_market_candle_coverage_market_timeframe",
        ),
    )


def downgrade() -> None:
    op.drop_table("market_candle_coverage")
