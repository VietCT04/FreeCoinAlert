"""Add Telegram connection persistence.

Revision ID: 20260730_0002
Revises: 20260728_0001
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0002"
down_revision: str | Sequence[str] | None = "20260728_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_connections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("connected_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "last_verified_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("degraded_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "disconnected_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("status_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "status IN ('connected', 'degraded', 'disconnected')",
            name="ck_telegram_connections_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_telegram_connections_user_id"),
        sa.UniqueConstraint(
            "telegram_user_id",
            name="uq_telegram_connections_telegram_user_id",
        ),
        sa.UniqueConstraint(
            "telegram_chat_id",
            name="uq_telegram_connections_telegram_chat_id",
        ),
    )
    op.create_table(
        "telegram_link_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", postgresql.BYTEA(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("consumed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_telegram_link_tokens_expires_after_created",
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR consumed_at >= created_at",
            name="ck_telegram_link_tokens_consumed_after_created",
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_telegram_link_tokens_revoked_after_created",
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR revoked_at IS NULL",
            name="ck_telegram_link_tokens_not_consumed_and_revoked",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_telegram_link_tokens_token_hash"),
    )
    op.create_table(
        "telegram_processed_updates",
        sa.Column("update_id", sa.BigInteger(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "received_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "processed_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "confirmation_sent_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "outcome IN ("
            "'linked', 'already_linked', 'invalid_token', 'expired_token', "
            "'consumed_token', 'revoked_token', 'ownership_conflict', "
            "'unsupported_update'"
            ")",
            name="ck_telegram_processed_updates_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["telegram_connections.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("update_id"),
    )
    op.create_index(
        "ix_telegram_link_tokens_user_id",
        "telegram_link_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_telegram_link_tokens_expires_at",
        "telegram_link_tokens",
        ["expires_at"],
    )
    op.create_index(
        "uq_telegram_link_tokens_active_user_id",
        "telegram_link_tokens",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("consumed_at IS NULL AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_telegram_link_tokens_active_user_id",
        table_name="telegram_link_tokens",
    )
    op.drop_index("ix_telegram_link_tokens_expires_at", table_name="telegram_link_tokens")
    op.drop_index("ix_telegram_link_tokens_user_id", table_name="telegram_link_tokens")
    op.drop_table("telegram_processed_updates")
    op.drop_table("telegram_link_tokens")
    op.drop_table("telegram_connections")
