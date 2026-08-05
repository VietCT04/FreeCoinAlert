"""Idempotent deterministic data seed for the isolated E2E database."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.db.repositories.market_candles import calculate_source_fingerprint
from freecoinalert_api.db.repositories.supported_markets import (
    list_product_markets,
    upsert_catalog_metadata,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.e2e import require_e2e_mode
from freecoinalert_api.market_data.catalog import (
    SUPPORTED_EXCHANGE,
    SUPPORTED_MARKET_TYPE,
    SUPPORTED_SYMBOLS,
    CatalogMetadata,
)


E2E_SEED_NAMESPACE = uuid.UUID("6d0f8fd4-e8df-4cbf-9d91-e2e84ac2c89b")
# Covers the 90-day analysis maximum, the 200-candle warm-up for 4h presets,
# and the completed-day gap used by the deterministic E2E clock.
SEED_DAYS = 126
SOURCE_BATCH_SIZE = 2_000


async def seed_database(settings: Settings) -> None:
    require_e2e_mode(settings)
    if settings.e2e_clock_now is None:
        raise RuntimeError("E2E_CLOCK_NOW is required for deterministic seed data.")

    seed_clock = settings.e2e_clock_now.astimezone(UTC)
    metadata = {
        symbol: CatalogMetadata(
            base_asset=symbol.removesuffix("USDT"),
            quote_asset="USDT",
            provider_status="trading",
            min_price=Decimal("0.000001"),
            max_price=Decimal("1000000000"),
            price_tick=Decimal("0.000001"),
            metadata_checked_at=seed_clock,
            status_reason=None,
        )
        for symbol in SUPPORTED_SYMBOLS
    }

    async with get_async_session_factory()() as session:
        async with session.begin():
            markets = list(await list_product_markets(session))
            if {market.symbol for market in markets} != set(SUPPORTED_SYMBOLS):
                raise RuntimeError("The E2E seed requires the approved market catalogue.")
            await upsert_catalog_metadata(session, metadata_by_symbol=metadata)
            for market in sorted(markets, key=lambda item: item.symbol):
                await _seed_market(
                    session,
                    market=market,
                    seed_clock=seed_clock,
                )


async def _seed_market(
    session,
    *,
    market: SupportedMarket,
    seed_clock: datetime,
) -> None:
    end_time = seed_clock.replace(minute=0, second=0, microsecond=0)
    start_time = _align_four_hour_boundary(end_time - timedelta(days=SEED_DAYS))
    expected_source_count = int((end_time - start_time) / timedelta(minutes=1))
    source_count = await _count_current_candles(
        session,
        market_id=market.id,
        timeframe="1m",
        start_time=start_time,
        end_time=end_time,
    )
    hourly_count = await _count_current_candles(
        session,
        market_id=market.id,
        timeframe="1h",
        start_time=start_time,
        end_time=end_time,
    )
    four_hour_count = await _count_current_candles(
        session,
        market_id=market.id,
        timeframe="4h",
        start_time=start_time,
        end_time=end_time,
    )
    expected_hourly_count = expected_source_count // 60
    expected_four_hour_count = expected_source_count // 240
    if (
        source_count == expected_source_count
        and hourly_count == expected_hourly_count
        and four_hour_count == expected_four_hour_count
    ):
        return
    if source_count or hourly_count or four_hour_count:
        raise RuntimeError("The E2E candle seed is partially present and cannot be resumed safely.")

    hourly_sources: list[MarketCandle] = []
    four_hour_sources: list[MarketCandle] = []
    pending_candles: list[MarketCandle] = []
    for index in range(expected_source_count):
        open_time = start_time + timedelta(minutes=index)
        source = _source_candle(
            market_id=market.id,
            symbol=market.symbol,
            index=index,
            open_time=open_time,
            seed_clock=seed_clock,
        )
        pending_candles.append(source)
        hourly_sources.append(source)
        four_hour_sources.append(source)
        if len(hourly_sources) == 60:
            pending_candles.append(_aggregate_candle(market.id, "1h", hourly_sources, seed_clock))
            hourly_sources.clear()
        if len(four_hour_sources) == 240:
            pending_candles.append(_aggregate_candle(market.id, "4h", four_hour_sources, seed_clock))
            four_hour_sources.clear()
        if len(pending_candles) >= SOURCE_BATCH_SIZE:
            await _insert_candles(session, pending_candles)
            pending_candles.clear()

    await _insert_candles(session, pending_candles)


async def _insert_candles(session, candles: Sequence[MarketCandle]) -> None:
    if not candles:
        return

    await session.execute(
        MarketCandle.__table__.insert(),
        [_candle_values(candle) for candle in candles],
    )


def _candle_values(candle: MarketCandle) -> dict[str, object]:
    return {
        "id": candle.id,
        "supported_market_id": candle.supported_market_id,
        "timeframe": candle.timeframe,
        "open_time": candle.open_time,
        "close_time": candle.close_time,
        "source_kind": candle.source_kind,
        "status": candle.status,
        "status_reason": candle.status_reason,
        "revision": candle.revision,
        "is_current": candle.is_current,
        "supersedes_candle_id": candle.supersedes_candle_id,
        "source_candle_count": candle.source_candle_count,
        "expected_source_candle_count": candle.expected_source_candle_count,
        "source_fingerprint": candle.source_fingerprint,
        "open_price": candle.open_price,
        "high_price": candle.high_price,
        "low_price": candle.low_price,
        "close_price": candle.close_price,
        "base_volume": candle.base_volume,
        "quote_volume": candle.quote_volume,
        "trade_count": candle.trade_count,
        "first_trade_id": candle.first_trade_id,
        "last_trade_id": candle.last_trade_id,
        "provider_event_time": candle.provider_event_time,
        "provider_close_time": candle.provider_close_time,
        "received_at": candle.received_at,
    }


async def _count_current_candles(
    session,
    *,
    market_id: uuid.UUID,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(MarketCandle)
            .where(
                MarketCandle.supported_market_id == market_id,
                MarketCandle.timeframe == timeframe,
                MarketCandle.is_current.is_(True),
                MarketCandle.open_time >= start_time,
                MarketCandle.open_time < end_time,
            )
        )
        or 0
    )


def _source_candle(
    *,
    market_id: uuid.UUID,
    symbol: str,
    index: int,
    open_time: datetime,
    seed_clock: datetime,
) -> MarketCandle:
    close_time = open_time + timedelta(minutes=1)
    open_price = _price(symbol, index)
    close_price = _price(symbol, index + 1)
    high_price = max(open_price, close_price) + Decimal("0.02")
    low_price = min(open_price, close_price) - Decimal("0.02")
    return MarketCandle(
        id=uuid.uuid5(E2E_SEED_NAMESPACE, f"{market_id}:1m:{open_time.isoformat()}"),
        supported_market_id=market_id,
        timeframe="1m",
        open_time=open_time,
        close_time=close_time,
        source_kind="binance_kline",
        status="complete",
        status_reason=None,
        revision=1,
        is_current=True,
        supersedes_candle_id=None,
        source_candle_count=1,
        expected_source_candle_count=1,
        source_fingerprint=None,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        base_volume=Decimal("1.000000"),
        quote_volume=close_price,
        trade_count=1,
        first_trade_id=index * 2,
        last_trade_id=index * 2 + 1,
        provider_event_time=close_time,
        provider_close_time=close_time - timedelta(milliseconds=1),
        received_at=seed_clock,
    )


def _aggregate_candle(
    market_id: uuid.UUID,
    timeframe: str,
    sources: Sequence[MarketCandle],
    seed_clock: datetime,
) -> MarketCandle:
    first = sources[0]
    last = sources[-1]
    open_time = first.open_time
    close_time = last.close_time
    return MarketCandle(
        id=uuid.uuid5(E2E_SEED_NAMESPACE, f"{market_id}:{timeframe}:{open_time.isoformat()}"),
        supported_market_id=market_id,
        timeframe=timeframe,
        open_time=open_time,
        close_time=close_time,
        source_kind="aggregate_1m",
        status="complete",
        status_reason=None,
        revision=1,
        is_current=True,
        supersedes_candle_id=None,
        source_candle_count=len(sources),
        expected_source_candle_count=len(sources),
        source_fingerprint=calculate_source_fingerprint(sources),
        open_price=first.open_price,
        high_price=max(candle.high_price for candle in sources),
        low_price=min(candle.low_price for candle in sources),
        close_price=last.close_price,
        base_volume=sum((candle.base_volume for candle in sources), Decimal("0")),
        quote_volume=sum((candle.quote_volume for candle in sources), Decimal("0")),
        trade_count=sum(candle.trade_count for candle in sources),
        first_trade_id=None,
        last_trade_id=None,
        provider_event_time=None,
        provider_close_time=None,
        received_at=seed_clock,
    )


def _price(symbol: str, index: int) -> Decimal:
    base = Decimal("100") + Decimal(str((SUPPORTED_SYMBOLS.index(symbol) + 1) * 10))
    if symbol == "XRPUSDT":
        return base
    if symbol == "ETHUSDT":
        movement = _mixed_event_movement(index)
        return (base + movement).quantize(Decimal("0.000001"))
    if symbol == "SOLUSDT":
        movement = _event_movement(index, period_hours=24, losing=True)
        return (base + movement).quantize(Decimal("0.000001"))
    if symbol == "BNBUSDT":
        movement = _event_movement(index, period_hours=12, losing=False)
        return (base + movement).quantize(Decimal("0.000001"))

    cycle = index % 1_440
    if cycle < 720:
        movement = Decimal(cycle) / Decimal("100")
    else:
        movement = Decimal(1_440 - cycle) / Decimal("100")
    return (base + movement + Decimal(index // 3_600) / Decimal("100")).quantize(
        Decimal("0.000001")
    )


def _mixed_event_movement(index: int) -> Decimal:
    hour = index // 60
    cycle = hour // 24
    return _event_movement(
        index,
        period_hours=24,
        losing=cycle % 5 == 4,
    )


def _event_movement(index: int, *, period_hours: int, losing: bool) -> Decimal:
    hour = index // 60
    minute = index % 60
    position = hour % period_hours
    current = _hourly_event_movement(position, losing=losing)
    following = _hourly_event_movement((position + 1) % period_hours, losing=losing)
    return current + (following - current) * Decimal(minute) / Decimal("60")


def _hourly_event_movement(position: int, *, losing: bool) -> Decimal:
    if position == 1:
        return Decimal("6")
    if 2 <= position <= 7:
        if losing:
            return Decimal(7 - position)
        return Decimal("6") + Decimal(position - 1) / Decimal("2")
    return Decimal("0")


def _align_four_hour_boundary(value: datetime) -> datetime:
    value = value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    return value.replace(hour=value.hour - value.hour % 4)


def main() -> None:
    settings = get_settings()
    asyncio.run(seed_database(settings))


if __name__ == "__main__":
    main()
