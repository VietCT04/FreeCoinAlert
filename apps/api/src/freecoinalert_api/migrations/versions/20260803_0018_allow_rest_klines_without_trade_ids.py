"""Allow REST klines without unavailable trade-ID fields."""

from collections.abc import Sequence

from alembic import op


revision: str = "20260803_0018"
down_revision: str | Sequence[str] | None = "20260803_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        type_="check",
    )
    op.create_check_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        "(source_kind = 'binance_kline' AND status IN ('complete', 'superseded') "
        "AND provider_event_time IS NOT NULL AND provider_close_time IS NOT NULL "
        "AND ((first_trade_id IS NULL AND last_trade_id IS NULL) "
        "OR (first_trade_id IS NOT NULL AND last_trade_id IS NOT NULL "
        "AND first_trade_id >= 0 AND last_trade_id >= first_trade_id))) "
        "OR (source_kind = 'binance_kline' AND status IN ('incomplete', 'invalid')) "
        "OR (source_kind = 'aggregate_1m' AND first_trade_id IS NULL "
        "AND last_trade_id IS NULL AND provider_event_time IS NULL "
        "AND provider_close_time IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        type_="check",
    )
    op.create_check_constraint(
        "ck_market_candles_provider_identity",
        "market_candles",
        "(source_kind = 'binance_kline' AND status IN ('complete', 'superseded') "
        "AND first_trade_id IS NOT NULL AND last_trade_id IS NOT NULL "
        "AND first_trade_id >= 0 AND last_trade_id >= first_trade_id "
        "AND provider_event_time IS NOT NULL AND provider_close_time IS NOT NULL) "
        "OR (source_kind = 'binance_kline' AND status IN ('incomplete', 'invalid')) "
        "OR (source_kind = 'aggregate_1m' AND first_trade_id IS NULL "
        "AND last_trade_id IS NULL AND provider_event_time IS NULL "
        "AND provider_close_time IS NULL)",
    )
