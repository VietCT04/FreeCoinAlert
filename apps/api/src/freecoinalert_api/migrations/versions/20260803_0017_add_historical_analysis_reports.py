"""Persist immutable historical-analysis reports and series."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260803_0017"
down_revision: str | Sequence[str] | None = "20260803_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_historical_analysis_runs_lifecycle",
        "historical_analysis_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_historical_analysis_runs_lifecycle",
        "historical_analysis_runs",
        "((status = 'queued' AND completed_at IS NULL AND failed_at IS NULL "
        "AND cancelled_at IS NULL AND cancellation_requested_at IS NULL) OR "
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
    )
    op.create_table(
        "historical_analysis_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_fingerprint", sa.String(64), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(64), nullable=False),
        sa.Column("engine_version", sa.String(64), nullable=False),
        sa.Column("assumption_version", sa.String(64), nullable=False),
        sa.Column("calculation_version", sa.String(64), nullable=False),
        sa.Column("market_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("preset_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("coverage_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("assumptions_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("analysis_start", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("analysis_end", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("analysis_candle_count", sa.Integer(), nullable=False),
        sa.Column("signal_count", sa.Integer(), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("winning_trade_count", sa.Integer(), nullable=False),
        sa.Column("losing_trade_count", sa.Integer(), nullable=False),
        sa.Column("flat_trade_count", sa.Integer(), nullable=False),
        sa.Column("overlapping_signal_count", sa.Integer(), nullable=False),
        sa.Column("insufficient_forward_signal_count", sa.Integer(), nullable=False),
        sa.Column("equity_exhausted_signal_count", sa.Integer(), nullable=False),
        sa.Column("initial_equity", sa.Numeric(38, 18), nullable=False),
        sa.Column("final_equity", sa.Numeric(38, 18), nullable=False),
        sa.Column("gross_return", sa.Numeric(38, 18), nullable=False),
        sa.Column("net_return", sa.Numeric(38, 18), nullable=False),
        sa.Column("maximum_drawdown", sa.Numeric(38, 18), nullable=False),
        sa.Column("win_rate", sa.Numeric(38, 18), nullable=True),
        sa.Column("win_rate_undefined_reason", sa.String(64), nullable=True),
        sa.Column("profit_factor", sa.Numeric(38, 18), nullable=True),
        sa.Column("profit_factor_undefined_reason", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "result_fingerprint ~ '^[0-9a-f]{64}$' AND dataset_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_historical_analysis_reports_fingerprints",
        ),
        sa.CheckConstraint(
            "analysis_end > analysis_start",
            name="ck_historical_analysis_reports_range",
        ),
        sa.CheckConstraint(
            "analysis_candle_count >= 0 AND signal_count >= 0 AND trade_count >= 0 "
            "AND winning_trade_count >= 0 AND losing_trade_count >= 0 AND flat_trade_count >= 0 "
            "AND overlapping_signal_count >= 0 AND insufficient_forward_signal_count >= 0 "
            "AND equity_exhausted_signal_count >= 0",
            name="ck_historical_analysis_reports_counts_nonnegative",
        ),
        sa.CheckConstraint(
            "initial_equity >= 0 AND final_equity >= 0",
            name="ck_historical_analysis_reports_equity_nonnegative",
        ),
        sa.CheckConstraint(
            "((win_rate IS NULL AND win_rate_undefined_reason IS NOT NULL) OR "
            "(win_rate IS NOT NULL AND win_rate_undefined_reason IS NULL "
            "AND win_rate >= 0 AND win_rate <= 1))",
            name="ck_historical_analysis_reports_win_rate",
        ),
        sa.CheckConstraint(
            "((profit_factor IS NULL AND profit_factor_undefined_reason IS NOT NULL) OR "
            "(profit_factor IS NOT NULL AND profit_factor_undefined_reason IS NULL "
            "AND profit_factor >= 0))",
            name="ck_historical_analysis_reports_profit_factor",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["historical_analysis_runs.id"],
            name="fk_historical_analysis_reports_run_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_historical_analysis_reports_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["historical_analysis_datasets.id"],
            name="fk_historical_analysis_reports_dataset_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_historical_analysis_reports_run_id"),
        sa.UniqueConstraint("dataset_id", name="uq_historical_analysis_reports_dataset_id"),
    )
    op.create_index(
        "ix_historical_analysis_reports_user_created",
        "historical_analysis_reports",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "historical_analysis_trades",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("signal_candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_candle_revision", sa.Integer(), nullable=False),
        sa.Column("signal_open_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("signal_close_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("signal_direction", sa.String(32), nullable=False),
        sa.Column("position_direction", sa.String(32), nullable=False),
        sa.Column("entry_candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_candle_revision", sa.Integer(), nullable=False),
        sa.Column("entry_open_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("entry_raw_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("entry_fill_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("exit_candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exit_candle_revision", sa.Integer(), nullable=False),
        sa.Column("exit_close_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("exit_raw_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("exit_fill_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("holding_candle_count", sa.Integer(), nullable=False),
        sa.Column("fee_rate", sa.Numeric(38, 18), nullable=False),
        sa.Column("slippage_rate", sa.Numeric(38, 18), nullable=False),
        sa.Column("equity_before", sa.Numeric(38, 18), nullable=False),
        sa.Column("gross_return", sa.Numeric(38, 18), nullable=False),
        sa.Column("net_return", sa.Numeric(38, 18), nullable=False),
        sa.Column("gross_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("net_pnl", sa.Numeric(38, 18), nullable=False),
        sa.Column("equity_after", sa.Numeric(38, 18), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_historical_analysis_trades_sequence"),
        sa.CheckConstraint(
            "signal_candle_revision >= 1 AND entry_candle_revision >= 1 AND exit_candle_revision >= 1",
            name="ck_historical_analysis_trades_revisions",
        ),
        sa.CheckConstraint(
            "signal_direction IN ('cross_above', 'cross_below')",
            name="ck_historical_analysis_trades_signal_direction",
        ),
        sa.CheckConstraint(
            "position_direction IN ('long', 'synthetic_short')",
            name="ck_historical_analysis_trades_position_direction",
        ),
        sa.CheckConstraint(
            "outcome IN ('win', 'loss', 'flat')",
            name="ck_historical_analysis_trades_outcome",
        ),
        sa.CheckConstraint(
            "entry_raw_price > 0 AND entry_fill_price > 0 AND exit_raw_price > 0 AND exit_fill_price > 0",
            name="ck_historical_analysis_trades_prices_positive",
        ),
        sa.CheckConstraint(
            "holding_candle_count > 0 AND fee_rate >= 0 AND slippage_rate >= 0",
            name="ck_historical_analysis_trades_execution_values",
        ),
        sa.CheckConstraint(
            "equity_before >= 0 AND equity_after >= 0",
            name="ck_historical_analysis_trades_equity_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["historical_analysis_reports.id"],
            name="fk_historical_analysis_trades_report_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_candle_id"],
            ["market_candles.id"],
            name="fk_historical_analysis_trades_signal_candle_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["entry_candle_id"],
            ["market_candles.id"],
            name="fk_historical_analysis_trades_entry_candle_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["exit_candle_id"],
            ["market_candles.id"],
            name="fk_historical_analysis_trades_exit_candle_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_id",
            "sequence",
            name="uq_historical_analysis_trades_report_sequence",
        ),
    )
    op.create_index(
        "ix_historical_analysis_trades_report_sequence",
        "historical_analysis_trades",
        ["report_id", "sequence"],
    )
    op.create_index(
        "ix_historical_analysis_trades_candle_id",
        "historical_analysis_trades",
        ["signal_candle_id", "entry_candle_id", "exit_candle_id"],
    )

    op.create_table(
        "historical_analysis_equity_points",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candle_revision", sa.Integer(), nullable=False),
        sa.Column("open_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("close_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("equity", sa.Numeric(38, 18), nullable=False),
        sa.Column("drawdown", sa.Numeric(38, 18), nullable=False),
        sa.Column("position_state", sa.String(32), nullable=False),
        sa.Column("active_trade_sequence", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sequence >= 0",
            name="ck_historical_analysis_equity_points_sequence",
        ),
        sa.CheckConstraint(
            "candle_revision >= 1",
            name="ck_historical_analysis_equity_points_revision",
        ),
        sa.CheckConstraint(
            "close_time > open_time",
            name="ck_historical_analysis_equity_points_time_order",
        ),
        sa.CheckConstraint(
            "equity >= 0 AND drawdown >= -1 AND drawdown <= 0",
            name="ck_historical_analysis_equity_points_values",
        ),
        sa.CheckConstraint(
            "position_state IN ('flat', 'long', 'synthetic_short')",
            name="ck_historical_analysis_equity_points_position_state",
        ),
        sa.CheckConstraint(
            "active_trade_sequence IS NULL OR active_trade_sequence >= 1",
            name="ck_historical_analysis_equity_points_active_trade",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["historical_analysis_reports.id"],
            name="fk_historical_analysis_equity_points_report_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candle_id"],
            ["market_candles.id"],
            name="fk_historical_analysis_equity_points_candle_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_id",
            "sequence",
            name="uq_historical_analysis_equity_points_report_sequence",
        ),
    )
    op.create_index(
        "ix_historical_analysis_equity_points_report_sequence",
        "historical_analysis_equity_points",
        ["report_id", "sequence"],
    )
    op.create_index(
        "ix_historical_analysis_equity_points_candle_id",
        "historical_analysis_equity_points",
        ["candle_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historical_analysis_equity_points_candle_id",
        table_name="historical_analysis_equity_points",
    )
    op.drop_index(
        "ix_historical_analysis_equity_points_report_sequence",
        table_name="historical_analysis_equity_points",
    )
    op.drop_table("historical_analysis_equity_points")
    op.drop_index(
        "ix_historical_analysis_trades_candle_id",
        table_name="historical_analysis_trades",
    )
    op.drop_index(
        "ix_historical_analysis_trades_report_sequence",
        table_name="historical_analysis_trades",
    )
    op.drop_table("historical_analysis_trades")
    op.drop_index(
        "ix_historical_analysis_reports_user_created",
        table_name="historical_analysis_reports",
    )
    op.drop_table("historical_analysis_reports")
    op.drop_constraint(
        "ck_historical_analysis_runs_lifecycle",
        "historical_analysis_runs",
        type_="check",
    )
    op.execute(
        sa.text(
            "UPDATE historical_analysis_runs SET started_at = NULL "
            "WHERE status = 'queued'"
        )
    )
    op.create_check_constraint(
        "ck_historical_analysis_runs_lifecycle",
        "historical_analysis_runs",
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
    )
