"""Add one-time price alert persistence.

Revision ID: 20260730_0005
Revises: 20260730_0004
Create Date: 2026-07-30 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0005"
down_revision: str | Sequence[str] | None = "20260730_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "price_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creation_idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("target_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("exchange_snapshot", sa.String(length=32), nullable=False),
        sa.Column("market_type_snapshot", sa.String(length=32), nullable=False),
        sa.Column("symbol_snapshot", sa.String(length=32), nullable=False),
        sa.Column("base_asset_snapshot", sa.String(length=32), nullable=False),
        sa.Column("quote_asset_snapshot", sa.String(length=32), nullable=False),
        sa.Column("price_tick_snapshot", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("status_reason", sa.String(length=64), nullable=True),
        sa.Column("last_relation", sa.String(length=16), nullable=True),
        sa.Column("last_evaluated_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("last_evaluated_provider_id", sa.BigInteger(), nullable=True),
        sa.Column("last_evaluated_provider_time", postgresql.TIMESTAMP(timezone=True), nullable=True),
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
        sa.Column("triggered_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("disabled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("failed_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("kind = 'price_cross'", name="ck_price_alerts_kind"),
        sa.CheckConstraint(
            "direction IN ('cross_above', 'cross_below')",
            name="ck_price_alerts_direction",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'triggered', 'disabled', 'deleted', 'failed')",
            name="ck_price_alerts_status",
        ),
        sa.CheckConstraint(
            "last_relation IS NULL OR last_relation IN ('below', 'equal', 'above')",
            name="ck_price_alerts_last_relation",
        ),
        sa.CheckConstraint(
            "target_price > 0 AND target_price <> 'NaN'::numeric "
            "AND target_price <> 'Infinity'::numeric",
            name="ck_price_alerts_target_price_finite",
        ),
        sa.CheckConstraint(
            "price_tick_snapshot > 0 AND price_tick_snapshot <> 'NaN'::numeric "
            "AND price_tick_snapshot <> 'Infinity'::numeric",
            name="ck_price_alerts_price_tick_snapshot_finite",
        ),
        sa.CheckConstraint(
            "(target_price % price_tick_snapshot) = 0",
            name="ck_price_alerts_target_price_tick",
        ),
        sa.CheckConstraint(
            "last_evaluated_provider_id IS NULL OR last_evaluated_provider_id >= 0",
            name="ck_price_alerts_provider_id_nonnegative",
        ),
        sa.CheckConstraint(
            "last_evaluated_price IS NULL OR (last_evaluated_price > 0 "
            "AND last_evaluated_price <> 'NaN'::numeric "
            "AND last_evaluated_price <> 'Infinity'::numeric)",
            name="ck_price_alerts_evaluated_price_finite",
        ),
        sa.CheckConstraint(
            "(last_relation IS NULL AND last_evaluated_price IS NULL "
            "AND last_evaluated_provider_id IS NULL "
            "AND last_evaluated_provider_time IS NULL) OR "
            "(last_relation IS NOT NULL AND last_evaluated_price IS NOT NULL "
            "AND last_evaluated_provider_id IS NOT NULL "
            "AND last_evaluated_provider_time IS NOT NULL)",
            name="ck_price_alerts_evaluation_state",
        ),
        sa.CheckConstraint(
            "(status = 'active' AND triggered_at IS NULL AND disabled_at IS NULL "
            "AND deleted_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'triggered' AND triggered_at IS NOT NULL AND disabled_at IS NULL "
            "AND deleted_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'disabled' AND triggered_at IS NULL AND disabled_at IS NOT NULL "
            "AND deleted_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'deleted' AND triggered_at IS NULL AND disabled_at IS NULL "
            "AND deleted_at IS NOT NULL AND failed_at IS NULL) OR "
            "(status = 'failed' AND triggered_at IS NULL AND disabled_at IS NULL "
            "AND deleted_at IS NULL AND failed_at IS NOT NULL)",
            name="ck_price_alerts_lifecycle_timestamps",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["supported_market_id"],
            ["supported_markets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["telegram_connection_id"],
            ["telegram_connections.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "creation_idempotency_key",
            name="uq_price_alerts_user_creation_idempotency_key",
        ),
    )
    op.create_table(
        "alert_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_identity", sa.String(length=160), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("market_type", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("base_asset", sa.String(length=32), nullable=False),
        sa.Column("quote_asset", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("target_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("trigger_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("provider_event_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_event_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("observed_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("observed_after_reconnect", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("event_type = 'price_crossed'", name="ck_alert_events_event_type"),
        sa.CheckConstraint(
            "direction IN ('cross_above', 'cross_below')",
            name="ck_alert_events_direction",
        ),
        sa.CheckConstraint(
            "trigger_identity ~ '^binance:spot:[A-Z0-9]+:aggTrade:[0-9]+$'",
            name="ck_alert_events_trigger_identity",
        ),
        sa.CheckConstraint(
            "target_price > 0 AND target_price <> 'NaN'::numeric "
            "AND target_price <> 'Infinity'::numeric",
            name="ck_alert_events_target_price_finite",
        ),
        sa.CheckConstraint(
            "trigger_price > 0 AND trigger_price <> 'NaN'::numeric "
            "AND trigger_price <> 'Infinity'::numeric",
            name="ck_alert_events_trigger_price_finite",
        ),
        sa.CheckConstraint("provider_event_id >= 0", name="ck_alert_events_provider_id_nonnegative"),
        sa.ForeignKeyConstraint(["alert_id"], ["price_alerts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["telegram_connection_id"],
            ["telegram_connections.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id", name="uq_alert_events_alert_id"),
        sa.UniqueConstraint(
            "alert_id",
            "trigger_identity",
            name="uq_alert_events_alert_trigger_identity",
        ),
    )
    op.create_index(
        "ix_price_alerts_user_created",
        "price_alerts",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_price_alerts_market_status",
        "price_alerts",
        ["supported_market_id", "status"],
    )
    op.create_index(
        "ix_price_alerts_connection_status",
        "price_alerts",
        ["telegram_connection_id", "status"],
    )
    op.create_index(
        "ix_price_alerts_active_market",
        "price_alerts",
        ["supported_market_id", "id"],
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_alert_events_user_created",
        "alert_events",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index("ix_alert_events_alert_id", "alert_events", ["alert_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_events_alert_id", table_name="alert_events")
    op.drop_index("ix_alert_events_user_created", table_name="alert_events")
    op.drop_index("ix_price_alerts_active_market", table_name="price_alerts")
    op.drop_index("ix_price_alerts_connection_status", table_name="price_alerts")
    op.drop_index("ix_price_alerts_market_status", table_name="price_alerts")
    op.drop_index("ix_price_alerts_user_created", table_name="price_alerts")
    op.drop_table("alert_events")
    op.drop_table("price_alerts")
