"""Add durable market symbol state snapshots.

Revision ID: 20260730_0006
Revises: 20260730_0005
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0006"
down_revision: str | Sequence[str] | None = "20260730_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_symbol_states",
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_provider_event_id", sa.BigInteger(), nullable=True),
        sa.Column("last_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("last_provider_trade_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_received_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("connection_generation", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('starting', 'live', 'stale', 'disconnected', 'error')",
            name="ck_market_symbol_states_status",
        ),
        sa.CheckConstraint(
            "last_provider_event_id IS NULL OR last_provider_event_id >= 0",
            name="ck_market_symbol_states_provider_id_nonnegative",
        ),
        sa.CheckConstraint(
            "last_price IS NULL OR (last_price > 0 AND last_price <> 'NaN'::numeric "
            "AND last_price <> 'Infinity'::numeric)",
            name="ck_market_symbol_states_price_finite",
        ),
        sa.ForeignKeyConstraint(
            ["supported_market_id"],
            ["supported_markets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("supported_market_id"),
    )


def downgrade() -> None:
    op.drop_table("market_symbol_states")
