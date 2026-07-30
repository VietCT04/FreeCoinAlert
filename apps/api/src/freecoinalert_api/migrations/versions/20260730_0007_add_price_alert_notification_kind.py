"""Allow price-alert Telegram notification jobs.

Revision ID: 20260730_0007
Revises: 20260730_0006
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260730_0007"
down_revision: str | Sequence[str] | None = "20260730_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_notification_outbox_kind", "notification_outbox", type_="check")
    op.create_check_constraint(
        "ck_notification_outbox_kind",
        "notification_outbox",
        "kind IN ('telegram_test', 'telegram_price_alert')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_notification_outbox_kind", "notification_outbox", type_="check")
    op.create_check_constraint(
        "ck_notification_outbox_kind",
        "notification_outbox",
        "kind = 'telegram_test'",
    )
