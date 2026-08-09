"""Persist exit metadata for configurable historical-analysis trades."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260809_0020"
down_revision: str | Sequence[str] | None = "20260809_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_EXIT_RULE_SNAPSHOT = '{"type":"max_holding_candles","candles":6}'


def upgrade() -> None:
    op.add_column(
        "historical_analysis_trades",
        sa.Column("exit_reason", sa.String(64), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("exit_price_basis", sa.String(64), nullable=True),
    )
    op.add_column(
        "historical_analysis_trades",
        sa.Column("exit_rule_snapshot", postgresql.JSONB(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE historical_analysis_trades
            SET exit_reason = 'max_holding_candles',
                exit_price_basis = 'confirmed_candle_close',
                exit_rule_snapshot = CAST(:snapshot AS jsonb)
            WHERE exit_reason IS NULL
            """
        ).bindparams(snapshot=_LEGACY_EXIT_RULE_SNAPSHOT)
    )

    op.alter_column(
        "historical_analysis_trades",
        "exit_reason",
        existing_type=sa.String(64),
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_trades",
        "exit_price_basis",
        existing_type=sa.String(64),
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_trades",
        "exit_rule_snapshot",
        existing_type=postgresql.JSONB(),
        nullable=False,
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


def downgrade() -> None:
    op.drop_constraint(
        "ck_historical_analysis_trades_exit_price_basis",
        "historical_analysis_trades",
        type_="check",
    )
    op.drop_constraint(
        "ck_historical_analysis_trades_exit_reason",
        "historical_analysis_trades",
        type_="check",
    )
    op.drop_column("historical_analysis_trades", "exit_rule_snapshot")
    op.drop_column("historical_analysis_trades", "exit_price_basis")
    op.drop_column("historical_analysis_trades", "exit_reason")
