"""Add durable signal Telegram fan-out dispatch and outbox references.

Revision ID: 20260802_0014
Revises: 20260802_0013
Create Date: 2026-08-02 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260802_0014"
down_revision: str | Sequence[str] | None = "20260802_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_telegram_dispatches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "signal_event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("last_subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "notification_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "skipped_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default=sa.text("10"),
            nullable=False,
        ),
        sa.Column(
            "available_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("locked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(64), nullable=True),
        sa.Column("completed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'retry_wait', 'completed', 'skipped', 'failed')",
            name="ck_signal_telegram_dispatches_status",
        ),
        sa.CheckConstraint(
            "notification_count >= 0",
            name="ck_signal_telegram_dispatches_notification_count",
        ),
        sa.CheckConstraint(
            "skipped_count >= 0",
            name="ck_signal_telegram_dispatches_skipped_count",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_signal_telegram_dispatches_attempt_count",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="ck_signal_telegram_dispatches_max_attempts",
        ),
        sa.CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_signal_telegram_dispatches_attempt_count_maximum",
        ),
        sa.ForeignKeyConstraint(
            ["signal_event_id"],
            ["signal_events.id"],
            name="fk_signal_telegram_dispatches_signal_event_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "signal_event_id",
            name="uq_signal_telegram_dispatches_signal_event",
        ),
    )
    op.create_index(
        "ix_signal_telegram_dispatches_claim",
        "signal_telegram_dispatches",
        ["status", "available_at", "created_at"],
    )
    op.create_index(
        "ix_signal_telegram_dispatches_processing",
        "signal_telegram_dispatches",
        ["status", "locked_at"],
    )

    op.add_column(
        "notification_outbox",
        sa.Column("signal_event_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("signal_subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_notification_outbox_signal_event_id",
        "notification_outbox",
        "signal_events",
        ["signal_event_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_notification_outbox_signal_subscription_id",
        "notification_outbox",
        "signal_subscriptions",
        ["signal_subscription_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "ck_notification_outbox_kind",
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "ck_notification_outbox_kind",
        "notification_outbox",
        "kind IN ('telegram_test', 'telegram_price_alert', 'telegram_preset_signal')",
    )
    op.create_check_constraint(
        "ck_notification_outbox_signal_references",
        "notification_outbox",
        "(kind = 'telegram_preset_signal' AND signal_event_id IS NOT NULL AND signal_subscription_id IS NOT NULL) OR "
        "(kind IN ('telegram_test', 'telegram_price_alert') AND signal_event_id IS NULL AND signal_subscription_id IS NULL)",
    )
    op.create_index(
        "ix_notification_outbox_signal_event_user",
        "notification_outbox",
        ["user_id", "signal_event_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'telegram_preset_signal'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_outbox_signal_event_user",
        table_name="notification_outbox",
    )
    op.drop_constraint(
        "ck_notification_outbox_signal_references",
        "notification_outbox",
        type_="check",
    )
    op.drop_constraint(
        "ck_notification_outbox_kind",
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "ck_notification_outbox_kind",
        "notification_outbox",
        "kind IN ('telegram_test', 'telegram_price_alert')",
    )
    op.drop_constraint(
        "fk_notification_outbox_signal_subscription_id",
        "notification_outbox",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_notification_outbox_signal_event_id",
        "notification_outbox",
        type_="foreignkey",
    )
    op.drop_column("notification_outbox", "signal_subscription_id")
    op.drop_column("notification_outbox", "signal_event_id")

    op.drop_index(
        "ix_signal_telegram_dispatches_processing",
        table_name="signal_telegram_dispatches",
    )
    op.drop_index(
        "ix_signal_telegram_dispatches_claim",
        table_name="signal_telegram_dispatches",
    )
    op.drop_table("signal_telegram_dispatches")
