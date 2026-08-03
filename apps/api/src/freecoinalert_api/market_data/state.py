import logging
import time
from datetime import datetime
from uuid import UUID

from freecoinalert_api.db.repositories.market_symbol_states import upsert_market_symbol_state
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.events import PriceEvent

logger = logging.getLogger(__name__)
SINGLETON_LOCK_KEY = "freecoinalert:market-stream:binance:spot"


class MarketStateRecorder:
    def __init__(self, *, write_interval_seconds: int) -> None:
        self._write_interval_seconds = write_interval_seconds
        self._last_write_at: dict[UUID, float] = {}
        self._latest_events: dict[UUID, PriceEvent] = {}

    async def handle_price_event(self, event: PriceEvent) -> None:
        self._latest_events[event.supported_market_id] = event
        now = time.monotonic()

        if now - self._last_write_at.get(event.supported_market_id, 0) < self._write_interval_seconds:
            return

        await self._write_event(event)

    async def mark_status(
        self,
        *,
        supported_market_id: UUID,
        status: str,
        status_reason: str | None,
    ) -> None:
        event = self._latest_events.get(supported_market_id)
        await self._write(
            supported_market_id=supported_market_id,
            status=status,
            status_reason=status_reason,
            event=event,
        )

    async def _write_event(self, event: PriceEvent) -> None:
        await self._write(
            supported_market_id=event.supported_market_id,
            status="live",
            status_reason=None,
            event=event,
        )
        logger.info("market.symbol.live symbol=%s", event.symbol)

    def get_latest_event(self, supported_market_id: UUID) -> PriceEvent | None:
        return self._latest_events.get(supported_market_id)

    async def _write(
        self,
        *,
        supported_market_id: UUID,
        status: str,
        status_reason: str | None,
        event: PriceEvent | None,
    ) -> None:
        try:
            async with get_async_session_factory()() as session:
                async with session.begin():
                    await upsert_market_symbol_state(
                        session,
                        supported_market_id=supported_market_id,
                        status=status,
                        last_provider_event_id=None if event is None else event.provider_event_id,
                        last_price=None if event is None else event.price,
                        last_provider_trade_at=None if event is None else event.provider_trade_time,
                        last_received_at=None if event is None else event.received_at,
                        connection_generation=None if event is None else event.connection_generation,
                        status_reason=status_reason,
                    )
        except Exception:
            logger.error(
                "market.state.write_failed supported_market_id=%s status=%s",
                supported_market_id,
                status,
            )
            return

        self._last_write_at[supported_market_id] = time.monotonic()
