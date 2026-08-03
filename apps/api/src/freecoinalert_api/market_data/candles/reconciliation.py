import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.repositories.market_candles import find_missing_one_minute_ranges
from freecoinalert_api.db.repositories.supported_markets import list_product_markets
from freecoinalert_api.db.session import get_async_engine, get_async_session_factory
from freecoinalert_api.market_data.binance_rest import BinanceMetadataError, BinancePublicMarketDataClient
from freecoinalert_api.market_data.candles.ingestion import CandleIngestionService
from freecoinalert_api.market_data.catalog import is_market_ready, utc_now
from freecoinalert_api.market_data.events import ClosedOneMinuteCandleEvent
from freecoinalert_api.market_data.state import SINGLETON_LOCK_KEY

logger = logging.getLogger(__name__)


async def reconcile_recent(
    *,
    hours: int,
    kind: str = "recent_reconciliation",
    acquire_lock: bool = True,
) -> int | None:
    settings = get_settings()
    maximum_hours = 180 * 24 if kind == "bootstrap" else 168
    if hours <= 0 or hours > maximum_hours:
        raise ValueError("Candle reconciliation range exceeds its approved bound.")
    connection = None
    if acquire_lock:
        connection = await get_async_engine().connect()
        acquired = await connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": SINGLETON_LOCK_KEY},
        )
        if not acquired:
            logger.info("market.candle.reconciliation_skipped category=market_stream_already_running")
            await connection.close()
            return 0
    try:
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        start = now - timedelta(hours=hours)
        async with get_async_session_factory()() as session:
            markets = [
                market for market in await list_product_markets(session)
                if is_market_ready(market, current_time=utc_now(), max_age_seconds=86400)
            ]
        client = BinancePublicMarketDataClient(base_url=settings.binance_spot_base_url)
        ingestion = CandleIngestionService()
        repaired = 0
        for market in markets:
            async with get_async_session_factory()() as session:
                gaps = await find_missing_one_minute_ranges(
                    session, supported_market_id=market.id, start_open_time=start, end_open_time=now
                )
            for gap in gaps:
                page_start = gap.start_open_time
                while page_start < gap.end_open_time:
                    page_end = min(page_start + timedelta(minutes=1000), gap.end_open_time)
                    klines = await client.get_spot_klines(
                        symbol=market.symbol,
                        start_open_time=page_start,
                        end_open_time=page_end,
                    )
                    events = []
                    for kline in klines:
                        events.append(ClosedOneMinuteCandleEvent(
                            exchange="binance", market_type="spot", supported_market_id=market.id,
                            symbol=market.symbol, timeframe="1m", open_time=kline.open_time,
                            close_time=kline.close_time, provider_close_time=kline.close_time - timedelta(milliseconds=1),
                            open_price=kline.open_price, high_price=kline.high_price, low_price=kline.low_price,
                            close_price=kline.close_price, base_volume=kline.base_volume, quote_volume=kline.quote_volume,
                            trade_count=kline.trade_count, first_trade_id=kline.first_trade_id,
                            last_trade_id=kline.last_trade_id, provider_event_time=datetime.now(UTC),
                            received_at=datetime.now(UTC), connection_generation=__import__("uuid").uuid4(),
                        ))
                    repaired += await ingestion.persist_closed_candles(events)
                    page_start = page_end
        logger.info("market.candle.reconciliation_completed kind=%s repaired=%s", kind, repaired)
        return None
    except BinanceMetadataError as error:
        logger.warning("market.candle.reconciliation_failed category=%s", error.category)
        return 1
    finally:
        if connection is not None:
            await connection.close()


def main() -> None:
    settings = get_settings()
    raise SystemExit(asyncio.run(reconcile_recent(hours=settings.candle_reconciliation_lookback_hours, kind="reconciliation")))


if __name__ == "__main__":
    main()
