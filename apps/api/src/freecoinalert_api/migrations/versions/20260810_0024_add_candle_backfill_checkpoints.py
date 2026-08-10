"""Add resumable public-archive candle backfill checkpoints."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260810_0024"
down_revision: str | Sequence[str] | None = "20260810_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        type_="check",
    )
    op.create_check_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        "(source_kind = 'binance_kline' AND status IN ('complete', 'superseded') "
        "AND provider_close_time IS NOT NULL "
        "AND ((first_trade_id IS NULL AND last_trade_id IS NULL) "
        "OR (first_trade_id IS NOT NULL AND last_trade_id IS NOT NULL "
        "AND first_trade_id >= 0 AND last_trade_id >= first_trade_id))) "
        "OR (source_kind = 'binance_kline' AND status IN ('incomplete', 'invalid')) "
        "OR (source_kind = 'aggregate_1m' AND first_trade_id IS NULL "
        "AND last_trade_id IS NULL AND provider_event_time IS NULL "
        "AND provider_close_time IS NULL)",
    )
    op.create_table(
        "candle_backfill_checkpoints",
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
        sa.Column("archive_granularity", sa.String(length=16), nullable=False),
        sa.Column("period_start", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("period_end", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("archive_key", sa.String(length=256), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("next_open_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_category", sa.String(length=64), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("exchange = 'binance'", name="ck_candle_backfill_exchange"),
        sa.CheckConstraint("market_type = 'spot'", name="ck_candle_backfill_market_type"),
        sa.CheckConstraint("timeframe = '1m'", name="ck_candle_backfill_timeframe"),
        sa.CheckConstraint(
            "archive_granularity IN ('monthly', 'daily')",
            name="ck_candle_backfill_granularity",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'complete', 'failed')",
            name="ck_candle_backfill_status",
        ),
        sa.CheckConstraint("period_end > period_start", name="ck_candle_backfill_period"),
        sa.CheckConstraint(
            "next_open_time >= period_start AND next_open_time <= period_end",
            name="ck_candle_backfill_next_open_time",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_candle_backfill_attempt_count"),
        sa.CheckConstraint(
            "checksum_sha256 IS NULL OR checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_candle_backfill_checksum",
        ),
        sa.ForeignKeyConstraint(
            ["supported_market_id"],
            ["supported_markets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("archive_key", name="uq_candle_backfill_archive_key"),
    )
    op.create_index(
        "ix_candle_backfill_status_next_open_time",
        "candle_backfill_checkpoints",
        ["status", "next_open_time"],
    )
    op.create_index(
        "ix_candle_backfill_market_period",
        "candle_backfill_checkpoints",
        ["supported_market_id", "period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candle_backfill_market_period",
        table_name="candle_backfill_checkpoints",
    )
    op.drop_index(
        "ix_candle_backfill_status_next_open_time",
        table_name="candle_backfill_checkpoints",
    )
    op.drop_table("candle_backfill_checkpoints")
    op.drop_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        type_="check",
    )
    op.create_check_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        "(source_kind = 'binance_kline' AND status IN ('complete', 'superseded') "
        "AND provider_event_time IS NOT NULL AND provider_close_time IS NOT NULL "
        "AND ((first_trade_id IS NULL AND last_trade_id IS NULL) "
        "OR (first_trade_id IS NOT NULL AND last_trade_id IS NOT NULL "
        "AND first_trade_id >= 0 AND last_trade_id >= first_trade_id))) "
        "OR (source_kind = 'binance_kline' AND status IN ('incomplete', 'invalid')) "
        "OR (source_kind = 'aggregate_1m' AND first_trade_id IS NULL "
        "AND last_trade_id IS NULL AND provider_event_time IS NULL "
        "AND provider_close_time IS NULL)",
    )
