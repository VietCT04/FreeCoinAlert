"""Add durable signal-feed stream sequencing and publication records.

Revision ID: 20260802_0012
Revises: 20260731_0011
Create Date: 2026-08-02 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260802_0012"
down_revision: str | Sequence[str] | None = "20260731_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_feed_stream_events",
        sa.Column("sequence", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("signal_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('signal_created', 'signal_invalidated')",
            name="ck_signal_feed_stream_events_kind",
        ),
        sa.ForeignKeyConstraint(
            ["signal_event_id"],
            ["signal_events.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("sequence"),
        sa.UniqueConstraint(
            "kind",
            "signal_event_id",
            name="uq_signal_feed_stream_events_kind_event",
        ),
    )
    op.create_index(
        "ix_signal_feed_stream_events_created_at",
        "signal_feed_stream_events",
        ["created_at"],
    )
    op.create_index(
        "ix_signal_feed_stream_events_signal_event_id",
        "signal_feed_stream_events",
        ["signal_event_id"],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO signal_feed_stream_events (kind, signal_event_id, created_at)
            SELECT 'signal_created', id, created_at
            FROM signal_events
            ORDER BY created_at ASC, id ASC
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_signal_feed_stream_events_signal_event_id",
        table_name="signal_feed_stream_events",
    )
    op.drop_index(
        "ix_signal_feed_stream_events_created_at",
        table_name="signal_feed_stream_events",
    )
    op.drop_table("signal_feed_stream_events")
