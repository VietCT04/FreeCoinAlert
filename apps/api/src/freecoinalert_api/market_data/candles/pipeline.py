import asyncio
import logging
from typing import Protocol

from freecoinalert_api.market_data.events import ConfirmedCandleEvent

logger = logging.getLogger(__name__)
CANDLE_PIPELINE_QUEUE_SIZE = 1000


class ConfirmedCandleSink(Protocol):
    async def handle_confirmed_candle(self, event: ConfirmedCandleEvent) -> None: ...


class ConfirmedCandlePipeline:
    def __init__(self, sinks: list[ConfirmedCandleSink]) -> None:
        self.queue: asyncio.Queue[ConfirmedCandleEvent] = asyncio.Queue(
            maxsize=CANDLE_PIPELINE_QUEUE_SIZE
        )
        self._sinks = sinks

    def enqueue(self, event: ConfirmedCandleEvent) -> None:
        self.queue.put_nowait(event)

    async def consume(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set() or not self.queue.empty():
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except TimeoutError:
                continue
            try:
                for sink in self._sinks:
                    await sink.handle_confirmed_candle(event)
            finally:
                self.queue.task_done()

    def log_backpressure(self) -> None:
        logger.error("market.candle.pipeline_backpressure queue_depth=%s", self.queue.qsize())
