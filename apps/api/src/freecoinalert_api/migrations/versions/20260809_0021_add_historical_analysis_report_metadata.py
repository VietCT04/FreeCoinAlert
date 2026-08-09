"""Persist immutable strategy and exit metadata on historical reports."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260809_0021"
down_revision: str | Sequence[str] | None = "20260809_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "historical_analysis_reports",
        sa.Column("strategy_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "historical_analysis_reports",
        sa.Column("strategy_fingerprint", sa.String(64), nullable=True),
    )
    op.add_column(
        "historical_analysis_reports",
        sa.Column(
            "exit_reason_counts_snapshot",
            postgresql.JSONB(),
            nullable=True,
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE historical_analysis_reports AS report
            SET strategy_snapshot = run.strategy_snapshot,
                strategy_fingerprint = run.strategy_fingerprint,
                exit_reason_counts_snapshot = jsonb_build_object(
                    'max_holding_candles', report.trade_count
                )
            FROM historical_analysis_runs AS run
            WHERE run.id = report.run_id
            """
        )
    )

    op.alter_column(
        "historical_analysis_reports",
        "strategy_snapshot",
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_reports",
        "strategy_fingerprint",
        nullable=False,
    )
    op.alter_column(
        "historical_analysis_reports",
        "exit_reason_counts_snapshot",
        nullable=False,
    )
    op.drop_constraint(
        "ck_historical_analysis_reports_fingerprints",
        "historical_analysis_reports",
        type_="check",
    )
    op.create_check_constraint(
        "ck_historical_analysis_reports_fingerprints",
        "historical_analysis_reports",
        "result_fingerprint ~ '^[0-9a-f]{64}$' "
        "AND dataset_fingerprint ~ '^[0-9a-f]{64}$' "
        "AND strategy_fingerprint ~ '^[0-9a-f]{64}$'",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_historical_analysis_reports_fingerprints",
        "historical_analysis_reports",
        type_="check",
    )
    op.create_check_constraint(
        "ck_historical_analysis_reports_fingerprints",
        "historical_analysis_reports",
        "result_fingerprint ~ '^[0-9a-f]{64}$' "
        "AND dataset_fingerprint ~ '^[0-9a-f]{64}$'",
    )
    op.drop_column("historical_analysis_reports", "exit_reason_counts_snapshot")
    op.drop_column("historical_analysis_reports", "strategy_fingerprint")
    op.drop_column("historical_analysis_reports", "strategy_snapshot")
