"""Add candle operational state.

Revision ID: 20260730_0009
Revises: 20260730_0008
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0009"
down_revision: str | Sequence[str] | None = "20260730_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candle_sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("requested_start", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("requested_end", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("current_market_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("next_open_time", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("source_rows_written", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("source_rows_unchanged", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("source_rows_corrected", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("derived_rows_written", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("unresolved_gap_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("started_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('bootstrap', 'reconciliation', 'recent_reconciliation', 'retention_cleanup')", name="ck_candle_sync_runs_kind"),
        sa.CheckConstraint("status IN ('running', 'succeeded', 'failed', 'cancelled')", name="ck_candle_sync_runs_status"),
        sa.CheckConstraint("requested_end > requested_start", name="ck_candle_sync_runs_range"),
        sa.ForeignKeyConstraint(["current_market_id"], ["supported_markets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "candle_symbol_states",
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("latest_complete_1m_open_time", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("latest_complete_1h_open_time", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("latest_complete_4h_open_time", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("last_websocket_received_at", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("last_reconciled_through", postgresql.TIMESTAMP(timezone=True)),
        sa.Column("unresolved_gap_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_reason", sa.String(64)),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('starting', 'live', 'stale', 'gapped', 'error')", name="ck_candle_symbol_states_status"),
        sa.CheckConstraint("unresolved_gap_count >= 0", name="ck_candle_symbol_states_gap_count"),
        sa.ForeignKeyConstraint(["supported_market_id"], ["supported_markets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("supported_market_id"),
    )


def downgrade() -> None:
    op.drop_table("candle_symbol_states")
    op.drop_table("candle_sync_runs")
