import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.repositories.market_candles import (
    CandleValues,
    upsert_closed_source_candle,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.candles.aggregation import rebuild_window, window_open_time
from freecoinalert_api.market_data.events import (
    CanonicalOneMinuteCandleInput,
    ClosedOneMinuteCandleEvent,
    ConfirmedCandleEvent,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CanonicalCandlePersistenceResult:
    changed_count: int
    changed_sources: tuple[tuple[CanonicalOneMinuteCandleInput, MarketCandle], ...]
    changed_derived: tuple[MarketCandle, ...]


def canonical_input_from_live_event(
    event: ClosedOneMinuteCandleEvent,
) -> CanonicalOneMinuteCandleInput:
    return CanonicalOneMinuteCandleInput(
        exchange=event.exchange,
        market_type=event.market_type,
        supported_market_id=event.supported_market_id,
        symbol=event.symbol,
        timeframe=event.timeframe,
        open_time=event.open_time,
        close_time=event.close_time,
        provider_close_time=event.provider_close_time,
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
        received_at=event.received_at,
    )


class CandleIngestionService:
    async def persist_closed_candle(
        self,
        event: ClosedOneMinuteCandleEvent,
    ) -> list[ConfirmedCandleEvent]:
        return await self._persist_live_inputs([canonical_input_from_live_event(event)])

    async def persist_closed_candles(
        self,
        events: Sequence[ClosedOneMinuteCandleEvent],
    ) -> int:
        return await self.persist_canonical_candles(
            [canonical_input_from_live_event(event) for event in events]
        )

    async def persist_canonical_candles(
        self,
        inputs: Sequence[CanonicalOneMinuteCandleInput],
    ) -> int:
        if not inputs:
            return 0

        async with get_async_session_factory()() as session:
            async with session.begin():
                result = await self.persist_canonical_candles_in_session(session, inputs)
        return result.changed_count

    async def persist_canonical_candles_in_session(
        self,
        session: AsyncSession,
        inputs: Sequence[CanonicalOneMinuteCandleInput],
    ) -> CanonicalCandlePersistenceResult:
        if not inputs:
            return CanonicalCandlePersistenceResult(0, (), ())

        changed_sources: list[tuple[CanonicalOneMinuteCandleInput, MarketCandle]] = []
        affected_windows: set[tuple[str, datetime]] = set()
        for candle_input in inputs:
            if candle_input.timeframe != "1m":
                raise ValueError("Canonical candle ingestion only accepts 1m inputs.")

            source_before = await self._current_revision(
                session,
                candle_input.supported_market_id,
                "1m",
                candle_input.open_time,
            )
            source = await upsert_closed_source_candle(
                session,
                supported_market_id=candle_input.supported_market_id,
                open_time=candle_input.open_time,
                values=self._source_values(candle_input),
            )
            if source_before == source.revision:
                continue

            changed_sources.append((candle_input, source))
            for timeframe in ("1h", "4h"):
                affected_windows.add(
                    (timeframe, window_open_time(candle_input.open_time, timeframe))
                )

        changed_derived: list[MarketCandle] = []
        received_at = inputs[-1].received_at
        for timeframe, open_time in sorted(affected_windows):
            aggregate = await rebuild_window(
                session,
                supported_market_id=inputs[0].supported_market_id,
                timeframe=timeframe,
                open_time=open_time,
                received_at=received_at,
            )
            if aggregate.status == "complete":
                changed_derived.append(aggregate)

        return CanonicalCandlePersistenceResult(
            changed_count=len(changed_sources),
            changed_sources=tuple(changed_sources),
            changed_derived=tuple(changed_derived),
        )

    async def _persist_live_inputs(
        self,
        inputs: Sequence[CanonicalOneMinuteCandleInput],
    ) -> list[ConfirmedCandleEvent]:
        if not inputs:
            return []

        async with get_async_session_factory()() as session:
            async with session.begin():
                result = await self.persist_canonical_candles_in_session(session, inputs)

        confirmed: list[ConfirmedCandleEvent] = []
        for candle_input, source in result.changed_sources:
            confirmed.append(self._confirmed(candle_input, source, corrected=source.revision > 1))
            if source.revision == 1 and source.open_time != candle_input.open_time:
                raise ValueError("Canonical source candle identity changed during persistence.")
        source_input = inputs[-1]
        for aggregate in result.changed_derived:
            confirmed.append(
                self._confirmed(
                    source_input,
                    aggregate,
                    corrected=aggregate.revision > 1,
                )
            )
        if not confirmed and len(inputs) == 1:
            logger.info(
                "market.candle.duplicate symbol=%s open_time=%s",
                source_input.symbol,
                source_input.open_time,
            )
        return confirmed

    async def _current_revision(
        self,
        session: AsyncSession,
        supported_market_id: UUID,
        timeframe: str,
        open_time: datetime,
    ) -> int | None:
        from freecoinalert_api.db.repositories.market_candles import get_current_candle

        current = await get_current_candle(
            session,
            supported_market_id=supported_market_id,
            timeframe=timeframe,
            open_time=open_time,
        )
        return None if current is None else current.revision

    def _source_values(self, candle_input: CanonicalOneMinuteCandleInput) -> CandleValues:
        return CandleValues(
            close_time=candle_input.close_time,
            source_candle_count=1,
            expected_source_candle_count=1,
            source_fingerprint=None,
            open_price=candle_input.open_price,
            high_price=candle_input.high_price,
            low_price=candle_input.low_price,
            close_price=candle_input.close_price,
            base_volume=candle_input.base_volume,
            quote_volume=candle_input.quote_volume,
            trade_count=candle_input.trade_count,
            first_trade_id=candle_input.first_trade_id,
            last_trade_id=candle_input.last_trade_id,
            provider_event_time=candle_input.provider_event_time,
            provider_close_time=candle_input.provider_close_time,
            received_at=candle_input.received_at,
        )

    def _confirmed(
        self,
        source_input: CanonicalOneMinuteCandleInput,
        candle: MarketCandle,
        *,
        corrected: bool,
    ) -> ConfirmedCandleEvent:
        return ConfirmedCandleEvent(
            candle_id=candle.id,
            candle_revision=candle.revision,
            supported_market_id=candle.supported_market_id,
            exchange=source_input.exchange,
            market_type=source_input.market_type,
            symbol=source_input.symbol,
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
            observed_at=source_input.received_at,
            corrected=corrected,
        )
