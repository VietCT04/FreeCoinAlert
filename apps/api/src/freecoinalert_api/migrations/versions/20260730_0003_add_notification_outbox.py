"""Add notification outbox.

Revision ID: 20260730_0003
Revises: 20260730_0002
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0003"
down_revision: str | Sequence[str] | None = "20260730_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("message_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("available_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("locked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.BigInteger(), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint("kind = 'telegram_test'", name="ck_notification_outbox_kind"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'retry_wait', 'sent', 'failed')", name="ck_notification_outbox_status"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_notification_outbox_attempt_count"),
        sa.CheckConstraint("max_attempts > 0", name="ck_notification_outbox_max_attempts"),
        sa.CheckConstraint("attempt_count <= max_attempts", name="ck_notification_outbox_attempt_count_maximum"),
        sa.CheckConstraint("status != 'sent' OR sent_at IS NOT NULL", name="ck_notification_outbox_sent_at"),
        sa.CheckConstraint("status != 'failed' OR failed_at IS NOT NULL", name="ck_notification_outbox_failed_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["telegram_connection_id"], ["telegram_connections.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_notification_outbox_user_idempotency_key"),
    )
    op.create_index("ix_notification_outbox_claim", "notification_outbox", ["status", "available_at", "created_at"])
    op.create_index("ix_notification_outbox_user_id", "notification_outbox", ["user_id"])
    op.create_index("ix_notification_outbox_telegram_connection_id", "notification_outbox", ["telegram_connection_id"])
    op.create_index("ix_notification_outbox_created_at", "notification_outbox", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_created_at", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_telegram_connection_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_user_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_claim", table_name="notification_outbox")
    op.drop_table("notification_outbox")
