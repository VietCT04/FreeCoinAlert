"""Add the shared Binance REST request-weight state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260810_0026"
down_revision: str | Sequence[str] | None = "20260810_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_rest_rate_state",
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("window_started_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("reserved_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_used_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_limit_weight", sa.Integer(), nullable=True),
        sa.Column("blocked_until", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("blocked_reason", sa.String(32), nullable=True),
        sa.Column("last_response_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "reserved_weight >= 0 AND provider_used_weight >= 0",
            name="ck_provider_rest_rate_state_weights_nonnegative",
        ),
        sa.CheckConstraint(
            "provider_limit_weight IS NULL OR provider_limit_weight > 0",
            name="ck_provider_rest_rate_state_limit_positive",
        ),
        sa.CheckConstraint(
            "blocked_reason IS NULL OR blocked_reason IN ('rate_limited', 'ip_banned')",
            name="ck_provider_rest_rate_state_block_reason",
        ),
        sa.PrimaryKeyConstraint("provider_key"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO provider_rest_rate_state (
                provider_key,
                window_started_at,
                reserved_weight,
                provider_used_weight,
                provider_limit_weight,
                blocked_until,
                blocked_reason,
                last_response_at
            )
            VALUES (
                'binance_spot_rest',
                date_trunc('minute', CURRENT_TIMESTAMP),
                0,
                0,
                NULL,
                NULL,
                NULL,
                NULL
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_table("provider_rest_rate_state")
