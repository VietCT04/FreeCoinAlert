"""Explicit, lock-protected historical signal-event rebuild command."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.db.session import get_async_engine
from freecoinalert_api.market_data.stream import SINGLETON_LOCK_KEY

logger = logging.getLogger(__name__)


async def run_backfill() -> int:
    """Reserve the singleton lock before the evaluator rebuild implementation runs.

    Historical writes intentionally require a live database and canonical candle coverage;
    this command performs neither provider access nor synthetic-candle repair.
    """
    settings = get_settings()
    connection = await get_async_engine().connect()
    try:
        acquired = await connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": SINGLETON_LOCK_KEY},
        )
        if not acquired:
            logger.error("signal.backfill.failed category=market_stream_already_running")
            return 1
        cutoff = datetime.now(UTC) - timedelta(days=settings.signal_history_days)
        markets = await connection.execute(
            select(SupportedMarket.id).where(SupportedMarket.product_enabled.is_(True))
        )
        if not list(markets.scalars()):
            logger.error("signal.backfill.failed category=no_ready_markets")
            return 1
        coverage = await connection.scalar(
            select(MarketCandle.id).where(
                MarketCandle.is_current.is_(True),
                MarketCandle.status == "complete",
                MarketCandle.timeframe.in_(("1h", "4h")),
                MarketCandle.open_time >= cutoff,
            ).limit(1)
        )
        if coverage is None:
            logger.error("signal.backfill.failed category=incomplete_candle_coverage")
            return 1
        logger.info("signal.backfill.started history_days=%s", settings.signal_history_days)
        logger.error("signal.backfill.failed category=evaluator_rebuild_required")
        return 1
    finally:
        await connection.close()


def main() -> None:
    raise SystemExit(asyncio.run(run_backfill()))


if __name__ == "__main__":
    main()
