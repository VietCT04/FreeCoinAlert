"""Add immutable historical-analysis dataset manifests."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260803_0016"
down_revision: str | Sequence[str] | None = "20260803_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historical_analysis_datasets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "supported_market_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "signal_preset_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column(
            "analysis_start",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "analysis_end",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "warmup_start",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("required_warmup_candles", sa.Integer(), nullable=False),
        sa.Column("warmup_candle_count", sa.Integer(), nullable=False),
        sa.Column("analysis_candle_count", sa.Integer(), nullable=False),
        sa.Column("total_candle_count", sa.Integer(), nullable=False),
        sa.Column(
            "first_open_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "last_close_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "prepared_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "stale_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'stale', 'failed')",
            name="ck_historical_analysis_datasets_status",
        ),
        sa.CheckConstraint(
            "timeframe IN ('1h', '4h')",
            name="ck_historical_analysis_datasets_timeframe",
        ),
        sa.CheckConstraint(
            "failure_code IS NULL OR failure_code IN ("
            "'historical_dataset_insufficient_warmup', "
            "'historical_dataset_gap_detected', "
            "'historical_dataset_incomplete', "
            "'historical_dataset_invalid', "
            "'historical_dataset_correction_race', "
            "'historical_dataset_too_large', "
            "'historical_dataset_unavailable', "
            "'historical_dataset_stale')",
            name="ck_historical_analysis_datasets_failure_code",
        ),
        sa.CheckConstraint(
            "required_warmup_candles >= 0 "
            "AND warmup_candle_count >= 0 "
            "AND analysis_candle_count >= 0 "
            "AND total_candle_count >= 0 "
            "AND total_candle_count <= 2500",
            name="ck_historical_analysis_datasets_counts_nonnegative",
        ),
        sa.CheckConstraint(
            "total_candle_count = warmup_candle_count + analysis_candle_count",
            name="ck_historical_analysis_datasets_count_sum",
        ),
        sa.CheckConstraint(
            "analysis_end > analysis_start",
            name="ck_historical_analysis_datasets_analysis_range",
        ),
        sa.CheckConstraint(
            "warmup_start < analysis_start",
            name="ck_historical_analysis_datasets_warmup_range",
        ),
        sa.CheckConstraint(
            "last_close_time > first_open_time",
            name="ck_historical_analysis_datasets_time_order",
        ),
        sa.CheckConstraint(
            "manifest_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_historical_analysis_datasets_fingerprint",
        ),
        sa.CheckConstraint(
            "((status = 'ready' AND failure_code IS NULL AND stale_at IS NULL) OR "
            "(status = 'failed' AND failure_code IS NOT NULL AND stale_at IS NULL) OR "
            "(status = 'stale' AND failure_code = 'historical_dataset_stale' "
            "AND stale_at IS NOT NULL))",
            name="ck_historical_analysis_datasets_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["historical_analysis_runs.id"],
            name="fk_historical_analysis_datasets_run_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supported_market_id"],
            ["supported_markets.id"],
            name="fk_historical_analysis_datasets_supported_market_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signal_preset_id"],
            ["signal_presets.id"],
            name="fk_historical_analysis_datasets_signal_preset_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            name="uq_historical_analysis_datasets_run_id",
        ),
    )
    op.create_index(
        "ix_historical_analysis_datasets_status_updated",
        "historical_analysis_datasets",
        ["status", "updated_at"],
    )

    op.create_table(
        "historical_analysis_dataset_candles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candle_revision", sa.Integer(), nullable=False),
        sa.Column("is_warmup", sa.Boolean(), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column(
            "open_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "close_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("open_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("high_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("low_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("close_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("base_volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("quote_volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("trade_count", sa.BigInteger(), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("source_candle_count", sa.Integer(), nullable=False),
        sa.Column("expected_source_candle_count", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_historical_analysis_dataset_candles_position",
        ),
        sa.CheckConstraint(
            "candle_revision >= 1",
            name="ck_historical_analysis_dataset_candles_revision",
        ),
        sa.CheckConstraint(
            "timeframe IN ('1h', '4h')",
            name="ck_historical_analysis_dataset_candles_timeframe",
        ),
        sa.CheckConstraint(
            "source_kind = 'aggregate_1m'",
            name="ck_historical_analysis_dataset_candles_source_kind",
        ),
        sa.CheckConstraint(
            "close_time > open_time",
            name="ck_historical_analysis_dataset_candles_time_order",
        ),
        sa.CheckConstraint(
            "close_time = open_time + CASE timeframe "
            "WHEN '1h' THEN INTERVAL '1 hour' "
            "ELSE INTERVAL '4 hours' END",
            name="ck_historical_analysis_dataset_candles_timeframe_duration",
        ),
        sa.CheckConstraint(
            "date_trunc('hour', open_time) = open_time "
            "AND (timeframe <> '4h' OR date_part('hour', open_time)::integer % 4 = 0)",
            name="ck_historical_analysis_dataset_candles_utc_boundary",
        ),
        sa.CheckConstraint(
            "source_candle_count = expected_source_candle_count "
            "AND expected_source_candle_count = CASE timeframe "
            "WHEN '1h' THEN 60 ELSE 240 END",
            name="ck_historical_analysis_dataset_candles_source_counts",
        ),
        sa.CheckConstraint(
            "source_fingerprint IS NULL OR source_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_historical_analysis_dataset_candles_source_fingerprint",
        ),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["historical_analysis_datasets.id"],
            name="fk_historical_analysis_dataset_candles_dataset_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candle_id"],
            ["market_candles.id"],
            name="fk_historical_analysis_dataset_candles_candle_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "position",
            name="uq_historical_analysis_dataset_candles_position",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "candle_id",
            name="uq_historical_analysis_dataset_candles_candle",
        ),
    )
    op.create_index(
        "ix_historical_analysis_dataset_candles_dataset_open_time",
        "historical_analysis_dataset_candles",
        ["dataset_id", "open_time"],
    )
    op.create_index(
        "ix_historical_analysis_dataset_candles_candle_dataset",
        "historical_analysis_dataset_candles",
        ["candle_id", "dataset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historical_analysis_dataset_candles_candle_dataset",
        table_name="historical_analysis_dataset_candles",
    )
    op.drop_index(
        "ix_historical_analysis_dataset_candles_dataset_open_time",
        table_name="historical_analysis_dataset_candles",
    )
    op.drop_table("historical_analysis_dataset_candles")
    op.drop_index(
        "ix_historical_analysis_datasets_status_updated",
        table_name="historical_analysis_datasets",
    )
    op.drop_table("historical_analysis_datasets")
