import asyncio
import logging
from typing import Protocol

from freecoinalert_api.market_data.events import PriceEvent

logger = logging.getLogger(__name__)
PIPELINE_QUEUE_SIZE = 10000


class PriceEventSink(Protocol):
    async def handle_price_event(self, event: PriceEvent) -> None: ...


class PriceEventPipeline:
    def __init__(self, sinks: list[PriceEventSink]) -> None:
        self.queue: asyncio.Queue[PriceEvent] = asyncio.Queue(maxsize=PIPELINE_QUEUE_SIZE)
        self._sinks = sinks

    def enqueue(self, event: PriceEvent) -> None:
        self.queue.put_nowait(event)

    async def consume(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set() or not self.queue.empty():
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=0.5)
            except TimeoutError:
                continue

            try:
                for sink in self._sinks:
                    await sink.handle_price_event(event)
            finally:
                self.queue.task_done()

    def log_backpressure(self) -> None:
        logger.error("market.pipeline.backpressure queue_depth=%s", self.queue.qsize())
