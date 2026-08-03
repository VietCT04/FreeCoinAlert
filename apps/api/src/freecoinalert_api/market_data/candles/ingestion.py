import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.repositories.market_candles import CandleValues, upsert_closed_source_candle
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.candles.aggregation import rebuild_window, window_open_time
from freecoinalert_api.market_data.events import ClosedOneMinuteCandleEvent, ConfirmedCandleEvent

logger = logging.getLogger(__name__)


class CandleIngestionService:
    async def persist_closed_candle(
        self,
        event: ClosedOneMinuteCandleEvent,
    ) -> list[ConfirmedCandleEvent]:
        async with get_async_session_factory()() as session:
            async with session.begin():
                source_before = await self._current_revision(
                    session, event.supported_market_id, "1m", event.open_time
                )
                source = await upsert_closed_source_candle(
                    session,
                    supported_market_id=event.supported_market_id,
                    open_time=event.open_time,
                    values=self._source_values(event),
                )
            if source_before == source.revision:
                logger.info("market.candle.duplicate symbol=%s open_time=%s", event.symbol, event.open_time)
                return []

        confirmed = [self._confirmed(event, source, corrected=source.revision > 1)]
        for timeframe in ("1h", "4h"):
            async with get_async_session_factory()() as session:
                async with session.begin():
                    aggregate = await rebuild_window(
                        session,
                        supported_market_id=event.supported_market_id,
                        timeframe=timeframe,
                        open_time=window_open_time(event.open_time, timeframe),
                        received_at=event.received_at,
                    )
                if aggregate.status == "complete":
                    confirmed.append(self._confirmed(event, aggregate, corrected=aggregate.revision > 1))
        return confirmed

    async def persist_closed_candles(
        self,
        events: Sequence[ClosedOneMinuteCandleEvent],
    ) -> int:
        if not events:
            return 0

        changed_count = 0
        affected_windows: set[tuple[str, datetime]] = set()
        async with get_async_session_factory()() as session:
            async with session.begin():
                for event in events:
                    source_before = await self._current_revision(
                        session, event.supported_market_id, "1m", event.open_time
                    )
                    source = await upsert_closed_source_candle(
                        session,
                        supported_market_id=event.supported_market_id,
                        open_time=event.open_time,
                        values=self._source_values(event),
                    )
                    if source_before == source.revision:
                        continue
                    changed_count += 1
                    for timeframe in ("1h", "4h"):
                        affected_windows.add((timeframe, window_open_time(event.open_time, timeframe)))

                received_at = events[-1].received_at
                for timeframe, open_time in sorted(affected_windows):
                    await rebuild_window(
                        session,
                        supported_market_id=events[0].supported_market_id,
                        timeframe=timeframe,
                        open_time=open_time,
                        received_at=received_at,
                    )

        return changed_count

    async def _current_revision(
        self,
        session: object,
        supported_market_id: UUID,
        timeframe: str,
        open_time: datetime,
    ) -> int | None:
        from freecoinalert_api.db.repositories.market_candles import get_current_candle

        current = await get_current_candle(
            session,  # type: ignore[arg-type]
            supported_market_id=supported_market_id,
            timeframe=timeframe,
            open_time=open_time,
        )
        return None if current is None else current.revision

    def _source_values(self, event: ClosedOneMinuteCandleEvent) -> CandleValues:
        return CandleValues(
            close_time=event.close_time,
            source_candle_count=1,
            expected_source_candle_count=1,
            source_fingerprint=None,
            open_price=event.open_price,
            high_price=event.high_price,
            low_price=event.low_price,
            close_price=event.close_price,
            base_volume=event.base_volume,
            quote_volume=event.quote_volume,
            trade_count=event.trade_count,
            first_trade_id=event.first_trade_id,
            last_trade_id=event.last_trade_id,
            provider_event_time=event.provider_event_time,
            provider_close_time=event.provider_close_time,
            received_at=event.received_at,
        )

    def _confirmed(
        self,
        source_event: ClosedOneMinuteCandleEvent,
        candle: MarketCandle,
        *,
        corrected: bool,
    ) -> ConfirmedCandleEvent:
        return ConfirmedCandleEvent(
            candle_id=candle.id,
            candle_revision=candle.revision,
            supported_market_id=candle.supported_market_id,
            exchange="binance",
            market_type="spot",
            symbol=source_event.symbol,
            timeframe=candle.timeframe,  # type: ignore[arg-type]
            open_time=candle.open_time.astimezone(UTC),
            close_time=candle.close_time.astimezone(UTC),
            open_price=candle.open_price,  # type: ignore[arg-type]
            high_price=candle.high_price,  # type: ignore[arg-type]
            low_price=candle.low_price,  # type: ignore[arg-type]
            close_price=candle.close_price,  # type: ignore[arg-type]
            base_volume=candle.base_volume,  # type: ignore[arg-type]
            quote_volume=candle.quote_volume,  # type: ignore[arg-type]
            trade_count=candle.trade_count,  # type: ignore[arg-type]
            source_kind=candle.source_kind,  # type: ignore[arg-type]
            observed_at=source_event.received_at,
            corrected=corrected,
        )
