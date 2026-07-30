import asyncio
import contextlib
import logging
import random
import signal
import time
import uuid
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from websockets.asyncio.client import connect

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.db.repositories.supported_markets import list_product_markets
from freecoinalert_api.db.session import get_async_engine, get_async_session_factory
from freecoinalert_api.market_data.binance_websocket import (
    BinanceWebSocketEventError,
    build_combined_stream_url,
    parse_aggregate_trade,
)
from freecoinalert_api.market_data.catalog import is_market_ready, utc_now
from freecoinalert_api.market_data.catalog_sync import synchronize_catalog
from freecoinalert_api.market_data.pipeline import PriceEventPipeline
from freecoinalert_api.market_data.state import MarketStateRecorder

logger = logging.getLogger(__name__)
SINGLETON_LOCK_KEY = "freecoinalert:market-stream:binance:spot"
CATALOG_MAXIMUM_AGE_SECONDS = 24 * 60 * 60
HEALTHY_CONNECTION_SECONDS = 60
PROACTIVE_RECONNECT_SECONDS = 23 * 60 * 60 + 50 * 60


class MarketStreamError(Exception):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class BinanceMarketStream:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.stop_event = asyncio.Event()
        self._last_accepted_ids: dict[str, int] = {}
        self._recorder = MarketStateRecorder(
            write_interval_seconds=self.settings.market_state_write_interval_seconds,
        )

    async def run(self) -> int:
        logger.info("market.stream.starting exchange=binance market_type=spot")
        self._install_signal_handlers()
        lock_connection = await self._acquire_singleton_lock()
        if lock_connection is None:
            logger.error("market.stream.singleton_rejected category=market_stream_already_running")
            return 1

        try:
            await self._run_until_stopped()
        finally:
            await lock_connection.close()

        return 0

    async def _run_until_stopped(self) -> None:
        reconnect_attempt = 0
        last_catalog_refresh = 0.0
        markets: dict[str, SupportedMarket] = {}

        while not self.stop_event.is_set():
            refresh_required = not markets or (
                time.monotonic() - last_catalog_refresh
                >= self.settings.market_catalog_refresh_seconds
            )
            if refresh_required:
                refreshed_markets = await self._refresh_catalog()
                last_catalog_refresh = time.monotonic()
                if refreshed_markets:
                    changed = set(refreshed_markets) != set(markets)
                    markets = refreshed_markets
                    if changed:
                        self._last_accepted_ids.clear()
                elif not markets:
                    await self._sleep_for_reconnect(reconnect_attempt, "catalog_unavailable")
                    reconnect_attempt += 1
                    continue

            generation = uuid.uuid4()
            started_at = time.monotonic()
            try:
                await self._run_connection(markets, generation)
            except MarketStreamError as error:
                category = error.category
            except Exception:
                category = "connection_error"

            if self.stop_event.is_set():
                break

            healthy = time.monotonic() - started_at >= HEALTHY_CONNECTION_SECONDS
            reconnect_attempt = 0 if healthy else reconnect_attempt + 1
            logger.warning(
                "market.stream.disconnected exchange=binance market_type=spot category=%s",
                category,
            )
            for market in markets.values():
                await self._recorder.mark_status(
                    supported_market_id=market.id,
                    status="disconnected",
                    status_reason=category,
                )
            await self._sleep_for_reconnect(reconnect_attempt, category)

    async def _run_connection(
        self,
        markets: dict[str, SupportedMarket],
        generation: uuid.UUID,
    ) -> None:
        url = build_combined_stream_url(self.settings.binance_spot_ws_base_url, markets)
        pipeline = PriceEventPipeline([self._recorder])
        consumer = asyncio.create_task(pipeline.consume(self.stop_event))
        freshness = asyncio.create_task(self._monitor_freshness(markets))
        observed_symbols: set[str] = set()
        self._last_accepted_ids.clear()

        for market in markets.values():
            await self._recorder.mark_status(
                supported_market_id=market.id,
                status="starting",
                status_reason=None,
            )

        try:
            async with connect(
                url,
                open_timeout=10,
                close_timeout=5,
                ping_interval=None,
                max_size=1024 * 1024,
                compression=None,
            ) as websocket:
                logger.info(
                    "market.stream.connected exchange=binance market_type=spot "
                    "symbol_count=%s connection_generation=%s",
                    len(markets),
                    generation,
                )
                try:
                    await asyncio.wait_for(
                        self._read_messages(
                            websocket,
                            markets,
                            generation,
                            pipeline,
                            observed_symbols,
                        ),
                        timeout=PROACTIVE_RECONNECT_SECONDS,
                    )
                except TimeoutError as error:
                    raise MarketStreamError("proactive_reconnect") from error
        except asyncio.QueueFull as error:
            pipeline.log_backpressure()
            raise MarketStreamError("backpressure") from error
        finally:
            freshness.cancel()
            if self.stop_event.is_set():
                await consumer
            else:
                consumer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await consumer
            with contextlib.suppress(asyncio.CancelledError):
                await freshness

        raise MarketStreamError("provider_closed")

    async def _read_messages(
        self,
        websocket: object,
        markets: dict[str, SupportedMarket],
        generation: uuid.UUID,
        pipeline: PriceEventPipeline,
        observed_symbols: set[str],
    ) -> None:
        async for raw_message in websocket:  # type: ignore[union-attr]
            if self.stop_event.is_set():
                return
            try:
                event = parse_aggregate_trade(
                    raw_message,
                    markets=markets,
                    received_at=datetime.now(UTC),
                    connection_generation=generation,
                    observed_after_reconnect=False,
                    max_age_seconds=self.settings.market_event_max_age_seconds,
                    future_tolerance_seconds=self.settings.market_event_future_tolerance_seconds,
                )
            except BinanceWebSocketEventError as error:
                logger.warning("market.event.invalid category=%s", error.category)
                continue

            previous_id = self._last_accepted_ids.get(event.symbol)
            if previous_id is not None and event.provider_event_id == previous_id:
                logger.info("market.event.duplicate symbol=%s provider_event_id=%s", event.symbol, previous_id)
                continue
            if previous_id is not None and event.provider_event_id < previous_id:
                logger.warning(
                    "market.event.out_of_order symbol=%s provider_event_id=%s last_provider_event_id=%s",
                    event.symbol,
                    event.provider_event_id,
                    previous_id,
                )
                continue
            if previous_id is not None and event.provider_event_id > previous_id + 1:
                logger.warning(
                    "market.event.sequence_jump symbol=%s provider_event_id=%s last_provider_event_id=%s",
                    event.symbol,
                    event.provider_event_id,
                    previous_id,
                )

            self._last_accepted_ids[event.symbol] = event.provider_event_id
            if event.symbol not in observed_symbols:
                event = replace(
                    event,
                    observed_after_reconnect=True,
                )
                observed_symbols.add(event.symbol)
            pipeline.enqueue(event)
            logger.info(
                "market.event.accepted symbol=%s provider_event_id=%s connection_generation=%s",
                event.symbol,
                event.provider_event_id,
                generation,
            )

    async def _refresh_catalog(self) -> dict[str, SupportedMarket]:
        result = await synchronize_catalog()
        async with get_async_session_factory()() as session:
            catalog = await list_product_markets(session)
        ready = {
            market.symbol: market
            for market in catalog
            if is_market_ready(
                market,
                current_time=utc_now(),
                max_age_seconds=CATALOG_MAXIMUM_AGE_SECONDS,
            )
        }
        if result != 0:
            logger.warning("market.catalog.refresh_failed using_previous_catalog=%s", bool(ready))
        if not ready:
            logger.error("market.stream.catalog_unavailable ready_symbol_count=0")
        return ready

    async def _monitor_freshness(self, markets: dict[str, SupportedMarket]) -> None:
        while not self.stop_event.is_set():
            await asyncio.sleep(2)
            now = datetime.now(UTC)
            for market in markets.values():
                event = self._recorder.get_latest_event(market.id)
                if event is None:
                    continue
                if (now - event.received_at).total_seconds() > self.settings.market_event_max_age_seconds:
                    logger.warning("market.symbol.stale symbol=%s", market.symbol)
                    await self._recorder.mark_status(
                        supported_market_id=market.id,
                        status="stale",
                        status_reason="freshness_timeout",
                    )

    async def _acquire_singleton_lock(self) -> AsyncConnection | None:
        connection = await get_async_engine().connect()
        acquired = await connection.scalar(
            text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
            {"lock_key": SINGLETON_LOCK_KEY},
        )
        if acquired:
            return connection
        await connection.close()
        return None

    async def _sleep_for_reconnect(self, attempt: int, category: str) -> None:
        delay = min(2 ** max(attempt - 1, 0), self.settings.market_stream_reconnect_max_seconds)
        jitter = random.uniform(0, delay * 0.25)
        logger.info(
            "market.stream.reconnecting exchange=binance market_type=spot category=%s "
            "attempt=%s delay_seconds=%s",
            category,
            attempt,
            delay + jitter,
        )
        try:
            await asyncio.wait_for(self.stop_event.wait(), timeout=delay + jitter)
        except TimeoutError:
            pass

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for signal_name in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(signal_name, self.stop_event.set)


async def run_stream() -> int:
    return await BinanceMarketStream().run()


def main() -> None:
    raise SystemExit(asyncio.run(run_stream()))


if __name__ == "__main__":
    main()
