"""Allow open-at-end historical trades to omit a realized outcome."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260810_0027"
down_revision: str | Sequence[str] | None = "20260810_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "historical_analysis_trades",
        "outcome",
        existing_type=sa.String(length=16),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM historical_analysis_trades
                    WHERE outcome IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'Cannot restore historical_analysis_trades.outcome NOT NULL '
                        'while open-at-end trades have NULL outcomes';
                END IF;
            END $$;
            """
        )
    )
    op.alter_column(
        "historical_analysis_trades",
        "outcome",
        existing_type=sa.String(length=16),
        nullable=False,
    )
