"""Add versioned signal presets and user subscriptions.

Revision ID: 20260730_0010
Revises: 20260730_0009
Create Date: 2026-07-30 00:00:00
"""

import hashlib
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0010"
down_revision: str | Sequence[str] | None = "20260730_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(96), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("strategy_type", sa.String(32), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("direction", sa.String(32), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("price_input", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("superseded_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("disabled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("version >= 1", name="ck_signal_presets_version"),
        sa.CheckConstraint("strategy_type IN ('price_sma_cross', 'rsi_threshold_cross')", name="ck_signal_presets_strategy_type"),
        sa.CheckConstraint("timeframe IN ('1h', '4h')", name="ck_signal_presets_timeframe"),
        sa.CheckConstraint("direction IN ('cross_above', 'cross_below')", name="ck_signal_presets_direction"),
        sa.CheckConstraint("price_input = 'close'", name="ck_signal_presets_price_input"),
        sa.CheckConstraint("status IN ('active', 'superseded', 'disabled')", name="ck_signal_presets_status"),
        sa.CheckConstraint("period > 0", name="ck_signal_presets_period"),
        sa.CheckConstraint("(strategy_type = 'price_sma_cross' AND period = 200 AND threshold IS NULL) OR (strategy_type = 'rsi_threshold_cross' AND period = 14 AND threshold = CASE WHEN direction = 'cross_above' THEN 70 ELSE 30 END)", name="ck_signal_presets_configuration"),
        sa.CheckConstraint("(status = 'active' AND superseded_at IS NULL AND disabled_at IS NULL) OR (status = 'superseded' AND superseded_at IS NOT NULL AND disabled_at IS NULL) OR (status = 'disabled' AND disabled_at IS NOT NULL)", name="ck_signal_presets_lifecycle"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_signal_presets_code_version"),
        sa.UniqueConstraint("configuration_hash", name="uq_signal_presets_configuration_hash"),
    )
    op.create_table(
        "signal_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_preset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("status_reason", sa.String(64), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("activated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("disabled_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_signal_subscriptions_status"),
        sa.CheckConstraint("(status = 'active' AND disabled_at IS NULL) OR (status = 'disabled' AND disabled_at IS NOT NULL)", name="ck_signal_subscriptions_lifecycle"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supported_market_id"], ["supported_markets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["signal_preset_id"], ["signal_presets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "supported_market_id", "signal_preset_id", name="uq_signal_subscriptions_combination"),
    )
    op.create_index("ix_signal_subscriptions_user_created", "signal_subscriptions", ["user_id", sa.text("created_at DESC"), sa.text("id DESC")])
    op.create_index("ix_signal_subscriptions_active_preset", "signal_subscriptions", ["signal_preset_id", "user_id"], postgresql_where=sa.text("status = 'active'"))
    _seed_initial_presets()


def _seed_initial_presets() -> None:
    rows = []
    for timeframe in ("1h", "4h"):
        for direction, phrase in (("cross_above", "above"), ("cross_below", "below")):
            rows.append((f"price_sma_200_cross_{phrase}_{timeframe}", "Price crosses " + phrase + " SMA 200", "Signals when the confirmed candle close moves " + ("from at or below SMA 200 to above it." if phrase == "above" else "from at or above SMA 200 to below it."), "price_sma_cross", timeframe, direction, 200, None))
        for direction, phrase, threshold in (("cross_above", "above", 70), ("cross_below", "below", 30)):
            rows.append((f"rsi_14_cross_{phrase}_{threshold}_{timeframe}", "RSI 14 crosses " + phrase + " " + str(threshold), "Signals when RSI 14 crosses " + phrase + " " + str(threshold) + " on confirmed candle closes.", "rsi_threshold_cross", timeframe, direction, 14, threshold))
    signal_presets = sa.table("signal_presets", sa.column("code", sa.String), sa.column("version", sa.Integer), sa.column("name", sa.String), sa.column("description", sa.String), sa.column("strategy_type", sa.String), sa.column("timeframe", sa.String), sa.column("direction", sa.String), sa.column("period", sa.Integer), sa.column("threshold", sa.Numeric), sa.column("price_input", sa.String), sa.column("status", sa.String), sa.column("configuration_hash", sa.String))
    for code, name, description, strategy_type, timeframe, direction, period, threshold in rows:
        threshold_value = "none" if threshold is None else str(threshold)
        calculation_version = (
            "sma_close_v1"
            if strategy_type == "price_sma_cross"
            else "rsi_wilder_close_v1"
        )
        canonical = (
            f"{strategy_type}|{timeframe}|{direction}|{period}|{threshold_value}|"
            f"close|{calculation_version}"
        )
        op.execute(signal_presets.insert().values(code=code, version=1, name=name, description=description, strategy_type=strategy_type, timeframe=timeframe, direction=direction, period=period, threshold=threshold, price_input="close", status="active", configuration_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest()))


def downgrade() -> None:
    op.drop_index("ix_signal_subscriptions_active_preset", table_name="signal_subscriptions")
    op.drop_index("ix_signal_subscriptions_user_created", table_name="signal_subscriptions")
    op.drop_table("signal_subscriptions")
    op.drop_table("signal_presets")
