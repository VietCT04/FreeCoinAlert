"""Add explicit Telegram delivery preference and subscription state history.

Revision ID: 20260802_0013
Revises: 20260802_0012
Create Date: 2026-08-02 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260802_0013"
down_revision: str | Sequence[str] | None = "20260802_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "signal_subscriptions",
        sa.Column(
            "telegram_delivery_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "signal_subscriptions",
        sa.Column(
            "telegram_delivery_changed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE signal_subscriptions SET telegram_delivery_enabled = false"
        )
    )
    op.create_table(
        "signal_subscription_state_events",
        sa.Column(
            "sequence",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
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
        sa.Column("subscription_status", sa.String(32), nullable=False),
        sa.Column("telegram_delivery_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "effective_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subscription_status IN ('active', 'disabled')",
            name="ck_signal_subscription_state_events_status",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["signal_subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supported_market_id"],
            ["supported_markets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signal_preset_id"],
            ["signal_presets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("sequence"),
    )
    op.create_index(
        "ix_signal_subscription_state_events_subscription_effective",
        "signal_subscription_state_events",
        [
            "subscription_id",
            sa.text("effective_at DESC"),
            sa.text("sequence DESC"),
        ],
    )
    op.create_index(
        "ix_signal_subscription_state_events_market_preset_effective",
        "signal_subscription_state_events",
        [
            "supported_market_id",
            "signal_preset_id",
            sa.text("effective_at DESC"),
            sa.text("sequence DESC"),
        ],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO signal_subscription_state_events (
                subscription_id,
                user_id,
                supported_market_id,
                signal_preset_id,
                subscription_status,
                telegram_delivery_enabled,
                effective_at
            )
            SELECT
                id,
                user_id,
                supported_market_id,
                signal_preset_id,
                status,
                false,
                CURRENT_TIMESTAMP
            FROM signal_subscriptions
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_signal_subscription_state_events_market_preset_effective",
        table_name="signal_subscription_state_events",
    )
    op.drop_index(
        "ix_signal_subscription_state_events_subscription_effective",
        table_name="signal_subscription_state_events",
    )
    op.drop_table("signal_subscription_state_events")
    op.drop_column("signal_subscriptions", "telegram_delivery_changed_at")
    op.drop_column("signal_subscriptions", "telegram_delivery_enabled")
