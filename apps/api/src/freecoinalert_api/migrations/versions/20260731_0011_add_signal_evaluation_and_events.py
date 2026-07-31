"""Add durable preset signal evaluation and immutable events.

Revision ID: 20260731_0011
Revises: 20260730_0010
Create Date: 2026-07-31 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260731_0011"
down_revision: str | Sequence[str] | None = "20260730_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_evaluation_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_preset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("status_reason", sa.String(64)),
        sa.Column("last_candle_id", postgresql.UUID(as_uuid=True)), sa.Column("last_candle_revision", sa.Integer()),
        sa.Column("last_candle_open_time", postgresql.TIMESTAMP(timezone=True)), sa.Column("last_relation", sa.String(16)),
        sa.Column("last_left_value", sa.Numeric(38, 18)), sa.Column("last_right_value", sa.Numeric(38, 18)),
        sa.Column("calculation_state_version", sa.Integer(), nullable=False), sa.Column("calculation_state", postgresql.JSONB(), nullable=False),
        sa.Column("initialized_at", postgresql.TIMESTAMP(timezone=True)), sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('warming', 'ready', 'stale', 'error', 'disabled')", name="ck_signal_evaluation_states_status"),
        sa.CheckConstraint("last_relation IS NULL OR last_relation IN ('below', 'equal', 'above')", name="ck_signal_evaluation_states_relation"),
        sa.CheckConstraint("calculation_state_version = 1", name="ck_signal_evaluation_states_calculation_version"),
        sa.ForeignKeyConstraint(["supported_market_id"], ["supported_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_preset_id"], ["signal_presets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["last_candle_id"], ["market_candles.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supported_market_id", "signal_preset_id", name="uq_signal_evaluation_states_market_preset"),
    )
    op.create_table(
        "signal_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("stream_sequence", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("supported_market_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("signal_preset_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("trigger_candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False), sa.Column("trigger_identity", sa.String(256), nullable=False),
        sa.Column("exchange_snapshot", sa.String(32), nullable=False), sa.Column("market_type_snapshot", sa.String(32), nullable=False), sa.Column("symbol_snapshot", sa.String(32), nullable=False), sa.Column("base_asset_snapshot", sa.String(32), nullable=False), sa.Column("quote_asset_snapshot", sa.String(32), nullable=False),
        sa.Column("preset_code_snapshot", sa.String(96), nullable=False), sa.Column("preset_version_snapshot", sa.Integer(), nullable=False), sa.Column("preset_name_snapshot", sa.String(128), nullable=False), sa.Column("strategy_type_snapshot", sa.String(32), nullable=False), sa.Column("calculation_version_snapshot", sa.String(64), nullable=False), sa.Column("timeframe_snapshot", sa.String(8), nullable=False), sa.Column("direction_snapshot", sa.String(32), nullable=False), sa.Column("period_snapshot", sa.Integer(), nullable=False), sa.Column("threshold_snapshot", sa.Numeric(38, 18)), sa.Column("price_input_snapshot", sa.String(32), nullable=False),
        sa.Column("candle_revision", sa.Integer(), nullable=False), sa.Column("candle_open_time", postgresql.TIMESTAMP(timezone=True), nullable=False), sa.Column("candle_close_time", postgresql.TIMESTAMP(timezone=True), nullable=False), sa.Column("previous_left_value", sa.Numeric(38, 18), nullable=False), sa.Column("previous_right_value", sa.Numeric(38, 18), nullable=False), sa.Column("current_left_value", sa.Numeric(38, 18), nullable=False), sa.Column("current_right_value", sa.Numeric(38, 18), nullable=False), sa.Column("candle_close_price", sa.Numeric(38, 18), nullable=False), sa.Column("backfilled", sa.Boolean(), nullable=False), sa.Column("occurred_at", postgresql.TIMESTAMP(timezone=True), nullable=False), sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("event_type = 'preset_crossed'", name="ck_signal_events_type"), sa.ForeignKeyConstraint(["supported_market_id"], ["supported_markets.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["signal_preset_id"], ["signal_presets.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["trigger_candle_id"], ["market_candles.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("stream_sequence", name="uq_signal_events_stream_sequence"), sa.UniqueConstraint("trigger_identity", name="uq_signal_events_trigger_identity"), sa.UniqueConstraint("supported_market_id", "signal_preset_id", "trigger_candle_id", "candle_revision", name="uq_signal_events_occurrence"),
    )
    op.create_table(
        "signal_event_invalidations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False), sa.Column("signal_event_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("reason", sa.String(64), nullable=False), sa.Column("replacement_candle_id", postgresql.UUID(as_uuid=True)), sa.Column("replacement_candle_revision", sa.Integer()), sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("reason IN ('candle_corrected', 'preset_disabled', 'calculation_invariant')", name="ck_signal_event_invalidations_reason"), sa.ForeignKeyConstraint(["signal_event_id"], ["signal_events.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["replacement_candle_id"], ["market_candles.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("signal_event_id", name="uq_signal_event_invalidations_event"),
    )
    op.create_index("ix_signal_events_occurred", "signal_events", [sa.text("occurred_at DESC"), "id"])
    op.create_index("ix_signal_events_market_preset_occurred", "signal_events", ["supported_market_id", "signal_preset_id", sa.text("occurred_at DESC")])
    op.create_index("ix_signal_events_trigger_candle", "signal_events", ["trigger_candle_id"])
    op.create_index("ix_signal_evaluation_states_status_updated", "signal_evaluation_states", ["status", "updated_at"])
    op.create_index("ix_signal_event_invalidations_event", "signal_event_invalidations", ["signal_event_id"])


def downgrade() -> None:
    op.drop_index("ix_signal_event_invalidations_event", table_name="signal_event_invalidations")
    op.drop_index("ix_signal_evaluation_states_status_updated", table_name="signal_evaluation_states")
    op.drop_index("ix_signal_events_trigger_candle", table_name="signal_events")
    op.drop_index("ix_signal_events_market_preset_occurred", table_name="signal_events")
    op.drop_index("ix_signal_events_occurred", table_name="signal_events")
    op.drop_table("signal_event_invalidations")
    op.drop_table("signal_events")
    op.drop_table("signal_evaluation_states")
