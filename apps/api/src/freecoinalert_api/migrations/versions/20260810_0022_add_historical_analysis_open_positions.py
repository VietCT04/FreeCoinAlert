"""Represent historical positions that remain open at range end."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260810_0022"
down_revision: str | Sequence[str] | None = "20260809_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "historical_analysis_reports",
        sa.Column("closed_trade_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "historical_analysis_reports",
        sa.Column("open_at_end_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "historical_analysis_reports",
        sa.Column("entry_unavailable_signal_count", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE historical_analysis_reports
            SET closed_trade_count = trade_count,
                open_at_end_count = 0,
                entry_unavailable_signal_count = 0
            """
        )
    )
    op.drop_constraint(
        "ck_historical_analysis_reports_counts_nonnegative",
        "historical_analysis_reports",
        type_="check",
    )
    op.create_check_constraint(
        "ck_historical_analysis_reports_counts_nonnegative",
        "historical_analysis_reports",
        "analysis_candle_count >= 0 AND signal_count >= 0 AND trade_count >= 0 "
        "AND winning_trade_count >= 0 AND losing_trade_count >= 0 AND flat_trade_count >= 0 "
        "AND overlapping_signal_count >= 0 AND insufficient_forward_signal_count >= 0 "
        "AND entry_unavailable_signal_count >= 0 AND equity_exhausted_signal_count >= 0 "
        "AND closed_trade_count >= 0 AND open_at_end_count >= 0",
    )
    op.alter_column(
        "historical_analysis_reports",
        "closed_trade_count",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_reports",
        "open_at_end_count",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_reports",
        "entry_unavailable_signal_count",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.add_column(
        "historical_analysis_trades",
        sa.Column("trade_status", sa.String(16), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("mark_candle_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("mark_candle_revision", sa.Integer(), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("mark_close_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("mark_price", sa.Numeric(38, 18), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("unrealized_return", sa.Numeric(38, 18), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("unrealized_pnl", sa.Numeric(38, 18), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE historical_analysis_trades SET trade_status = 'closed' "
            "WHERE trade_status IS NULL"
        )
    )

    for constraint_name in (
        "ck_historical_analysis_trades_revisions",
        "ck_historical_analysis_trades_outcome",
        "ck_historical_analysis_trades_exit_reason",
        "ck_historical_analysis_trades_exit_price_basis",
        "ck_historical_analysis_trades_prices_positive",
    ):
        op.drop_constraint(
            constraint_name,
            "historical_analysis_trades",
            type_="check",
        )

    for column_name, existing_type in (
        ("trade_status", sa.String(16)),
        ("exit_candle_id", postgresql.UUID(as_uuid=True)),
        ("exit_candle_revision", sa.Integer()),
        ("exit_close_time", sa.DateTime(timezone=True)),
        ("exit_raw_price", sa.Numeric(38, 18)),
        ("exit_fill_price", sa.Numeric(38, 18)),
        ("exit_reason", sa.String(64)),
        ("exit_price_basis", sa.String(64)),
        ("exit_rule_snapshot", postgresql.JSONB()),
    ):
        op.alter_column(
            "historical_analysis_trades",
            column_name,
            existing_type=existing_type,
            nullable=(column_name != "trade_status"),
        )

    op.alter_column(
        "historical_analysis_trades",
        "trade_status",
        existing_type=sa.String(16),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_historical_analysis_trades_mark_candle_id",
        "historical_analysis_trades",
        "market_candles",
        ["mark_candle_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_historical_analysis_trades_mark_candle_id",
        "historical_analysis_trades",
        ["mark_candle_id"],
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_status",
        "historical_analysis_trades",
        "trade_status IN ('closed', 'open_at_end')",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_revisions",
        "historical_analysis_trades",
        "signal_candle_revision >= 1 AND entry_candle_revision >= 1 "
        "AND (exit_candle_revision IS NULL OR exit_candle_revision >= 1) "
        "AND (mark_candle_revision IS NULL OR mark_candle_revision >= 1)",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_outcome",
        "historical_analysis_trades",
        "((trade_status = 'closed' AND outcome IN ('win', 'loss', 'flat')) OR "
        "(trade_status = 'open_at_end' AND outcome IS NULL))",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_exit_reason",
        "historical_analysis_trades",
        "((trade_status = 'closed' AND exit_reason IN ('stop_loss_percent', "
        "'take_profit_percent', 'rsi_threshold_cross', 'max_holding_candles')) OR "
        "(trade_status = 'open_at_end' AND exit_reason IS NULL))",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_exit_price_basis",
        "historical_analysis_trades",
        "((trade_status = 'closed' AND exit_price_basis IN ('stop_loss_level', "
        "'take_profit_level', 'gap_open', 'confirmed_candle_close')) OR "
        "(trade_status = 'open_at_end' AND exit_price_basis IS NULL))",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_prices_positive",
        "historical_analysis_trades",
        "entry_raw_price > 0 AND entry_fill_price > 0 AND "
        "((trade_status = 'closed' AND exit_candle_id IS NOT NULL "
        "AND exit_candle_revision IS NOT NULL AND exit_close_time IS NOT NULL "
        "AND exit_raw_price > 0 AND exit_fill_price > 0 "
        "AND mark_candle_id IS NULL AND mark_candle_revision IS NULL "
        "AND mark_close_time IS NULL AND mark_price IS NULL "
        "AND unrealized_return IS NULL AND unrealized_pnl IS NULL) OR "
        "(trade_status = 'open_at_end' AND exit_candle_id IS NULL "
        "AND exit_candle_revision IS NULL AND exit_close_time IS NULL "
        "AND exit_raw_price IS NULL "
        "AND exit_fill_price IS NULL AND mark_candle_id IS NOT NULL "
        "AND mark_candle_revision IS NOT NULL AND mark_close_time IS NOT NULL "
        "AND mark_price > 0 AND unrealized_return IS NOT NULL "
        "AND unrealized_pnl IS NOT NULL))",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_exit_rule_snapshot",
        "historical_analysis_trades",
        "((trade_status = 'closed' AND exit_rule_snapshot IS NOT NULL) OR "
        "(trade_status = 'open_at_end' AND exit_rule_snapshot IS NULL))",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM historical_analysis_trades
                    WHERE trade_status = 'open_at_end'
                ) THEN
                    RAISE EXCEPTION 'Cannot downgrade while open-at-end trades exist';
                END IF;
            END $$;
            """
        )
    )
    for constraint_name in (
        "ck_historical_analysis_trades_exit_rule_snapshot",
        "ck_historical_analysis_trades_prices_positive",
        "ck_historical_analysis_trades_exit_price_basis",
        "ck_historical_analysis_trades_exit_reason",
        "ck_historical_analysis_trades_outcome",
        "ck_historical_analysis_trades_revisions",
        "ck_historical_analysis_trades_status",
    ):
        op.drop_constraint(
            constraint_name,
            "historical_analysis_trades",
            type_="check",
        )
    op.drop_index(
        "ix_historical_analysis_trades_mark_candle_id",
        table_name="historical_analysis_trades",
    )
    op.drop_constraint(
        "fk_historical_analysis_trades_mark_candle_id",
        "historical_analysis_trades",
        type_="foreignkey",
    )
    for column_name, existing_type in (
        ("exit_candle_id", postgresql.UUID(as_uuid=True)),
        ("exit_candle_revision", sa.Integer()),
        ("exit_close_time", sa.DateTime(timezone=True)),
        ("exit_raw_price", sa.Numeric(38, 18)),
        ("exit_fill_price", sa.Numeric(38, 18)),
        ("exit_reason", sa.String(64)),
        ("exit_price_basis", sa.String(64)),
        ("exit_rule_snapshot", postgresql.JSONB()),
    ):
        op.alter_column(
            "historical_analysis_trades",
            column_name,
            existing_type=existing_type,
            nullable=False,
        )
    op.drop_column("historical_analysis_trades", "unrealized_pnl")
    op.drop_column("historical_analysis_trades", "unrealized_return")
    op.drop_column("historical_analysis_trades", "mark_price")
    op.drop_column("historical_analysis_trades", "mark_close_time")
    op.drop_column("historical_analysis_trades", "mark_candle_revision")
    op.drop_column("historical_analysis_trades", "mark_candle_id")
    op.drop_column("historical_analysis_trades", "trade_status")
    op.create_check_constraint(
        "ck_historical_analysis_trades_revisions",
        "historical_analysis_trades",
        "signal_candle_revision >= 1 AND entry_candle_revision >= 1 "
        "AND exit_candle_revision >= 1",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_outcome",
        "historical_analysis_trades",
        "outcome IN ('win', 'loss', 'flat')",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_exit_reason",
        "historical_analysis_trades",
        "exit_reason IN ('stop_loss_percent', 'take_profit_percent', "
        "'rsi_threshold_cross', 'max_holding_candles')",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_exit_price_basis",
        "historical_analysis_trades",
        "exit_price_basis IN ('stop_loss_level', 'take_profit_level', "
        "'gap_open', 'confirmed_candle_close')",
    )
    op.create_check_constraint(
        "ck_historical_analysis_trades_prices_positive",
        "historical_analysis_trades",
        "entry_raw_price > 0 AND entry_fill_price > 0 "
        "AND exit_raw_price > 0 AND exit_fill_price > 0",
    )

    op.drop_constraint(
        "ck_historical_analysis_reports_counts_nonnegative",
        "historical_analysis_reports",
        type_="check",
    )
    op.drop_column("historical_analysis_reports", "entry_unavailable_signal_count")
    op.drop_column("historical_analysis_reports", "open_at_end_count")
    op.drop_column("historical_analysis_reports", "closed_trade_count")
    op.create_check_constraint(
        "ck_historical_analysis_reports_counts_nonnegative",
        "historical_analysis_reports",
        "analysis_candle_count >= 0 AND signal_count >= 0 AND trade_count >= 0 "
        "AND winning_trade_count >= 0 AND losing_trade_count >= 0 AND flat_trade_count >= 0 "
        "AND overlapping_signal_count >= 0 AND insufficient_forward_signal_count >= 0 "
        "AND equity_exhausted_signal_count >= 0",
    )
