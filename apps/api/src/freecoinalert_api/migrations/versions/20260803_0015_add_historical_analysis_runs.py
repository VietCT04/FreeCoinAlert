"""Add owner-scoped historical-analysis runs."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260803_0015"
down_revision: str | Sequence[str] | None = "20260802_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historical_analysis_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column(
            "idempotency_key",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("exchange_snapshot", sa.String(32), nullable=False),
        sa.Column("market_type_snapshot", sa.String(32), nullable=False),
        sa.Column("symbol_snapshot", sa.String(32), nullable=False),
        sa.Column("base_asset_snapshot", sa.String(32), nullable=False),
        sa.Column("quote_asset_snapshot", sa.String(32), nullable=False),
        sa.Column("preset_code_snapshot", sa.String(96), nullable=False),
        sa.Column("preset_version_snapshot", sa.Integer(), nullable=False),
        sa.Column("preset_name_snapshot", sa.String(128), nullable=False),
        sa.Column("strategy_type_snapshot", sa.String(32), nullable=False),
        sa.Column("timeframe_snapshot", sa.String(8), nullable=False),
        sa.Column("direction_snapshot", sa.String(32), nullable=False),
        sa.Column("period_snapshot", sa.Integer(), nullable=False),
        sa.Column(
            "threshold_snapshot",
            sa.Numeric(precision=38, scale=18),
            nullable=True,
        ),
        sa.Column("price_input_snapshot", sa.String(32), nullable=False),
        sa.Column(
            "calculation_version_snapshot",
            sa.String(64),
            nullable=False,
        ),
        sa.Column("simulation_version", sa.String(64), nullable=False),
        sa.Column("assumption_version", sa.String(64), nullable=False),
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
        sa.Column("progress_stage", sa.String(32), nullable=False),
        sa.Column(
            "progress_percent",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default=sa.text("3"),
            nullable=False,
        ),
        sa.Column(
            "available_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "locked_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("locked_by", sa.String(64), nullable=True),
        sa.Column(
            "cancellation_requested_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "failed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("failure_code", sa.String(64), nullable=True),
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
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_historical_analysis_runs_status",
        ),
        sa.CheckConstraint(
            "analysis_end > analysis_start",
            name="ck_historical_analysis_runs_range",
        ),
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_historical_analysis_runs_progress_percent",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND max_attempts > 0 AND attempt_count <= max_attempts",
            name="ck_historical_analysis_runs_attempts",
        ),
        sa.CheckConstraint(
            "((status = 'queued' AND started_at IS NULL AND completed_at IS NULL "
            "AND failed_at IS NULL AND cancelled_at IS NULL "
            "AND cancellation_requested_at IS NULL) OR "
            "(status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL "
            "AND failed_at IS NULL AND cancelled_at IS NULL) OR "
            "(status = 'succeeded' AND started_at IS NOT NULL "
            "AND completed_at IS NOT NULL AND failed_at IS NULL "
            "AND cancelled_at IS NULL AND cancellation_requested_at IS NULL) OR "
            "(status = 'failed' AND started_at IS NOT NULL "
            "AND failed_at IS NOT NULL AND completed_at IS NULL "
            "AND cancelled_at IS NULL AND cancellation_requested_at IS NULL) OR "
            "(status = 'cancelled' AND cancelled_at IS NOT NULL AND completed_at IS NULL "
            "AND failed_at IS NULL AND cancellation_requested_at IS NOT NULL))",
            name="ck_historical_analysis_runs_lifecycle",
        ),
        sa.CheckConstraint(
            "((status = 'failed' AND failure_code IS NOT NULL) OR "
            "(status <> 'failed' AND failure_code IS NULL))",
            name="ck_historical_analysis_runs_failure_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_historical_analysis_runs_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supported_market_id"],
            ["supported_markets.id"],
            name="fk_historical_analysis_runs_supported_market_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signal_preset_id"],
            ["signal_presets.id"],
            name="fk_historical_analysis_runs_signal_preset_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_historical_analysis_runs_user_idempotency_key",
        ),
    )
    op.create_index(
        "ix_historical_analysis_runs_user_created",
        "historical_analysis_runs",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_historical_analysis_runs_queued_available",
        "historical_analysis_runs",
        ["available_at", "created_at"],
        postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index(
        "ix_historical_analysis_runs_active_user",
        "historical_analysis_runs",
        ["user_id", "created_at"],
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historical_analysis_runs_active_user",
        table_name="historical_analysis_runs",
    )
    op.drop_index(
        "ix_historical_analysis_runs_queued_available",
        table_name="historical_analysis_runs",
    )
    op.drop_index(
        "ix_historical_analysis_runs_user_created",
        table_name="historical_analysis_runs",
    )
    op.drop_table("historical_analysis_runs")
