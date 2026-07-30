from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.repositories.market_candles import (
    CandleValues,
    calculate_source_fingerprint,
    list_current_source_window,
    record_incomplete_window,
    replace_derived_candle,
)


def window_open_time(open_time: datetime, timeframe: str) -> datetime:
    utc_time = open_time.astimezone(UTC).replace(second=0, microsecond=0)
    if timeframe == "1h":
        return utc_time.replace(minute=0)
    if timeframe == "4h":
        return utc_time.replace(minute=0, hour=utc_time.hour - utc_time.hour % 4)
    raise ValueError("Only derived candle timeframes are supported.")


def expected_source_count(timeframe: str) -> int:
    return 60 if timeframe == "1h" else 240


async def rebuild_window(
    session: AsyncSession,
    *,
    supported_market_id: UUID,
    timeframe: str,
    open_time: datetime,
    received_at: datetime,
) -> MarketCandle:
    open_time = window_open_time(open_time, timeframe)
    expected_count = expected_source_count(timeframe)
    close_time = open_time + timedelta(minutes=expected_count)
    sources = await list_current_source_window(
        session,
        supported_market_id=supported_market_id,
        start_open_time=open_time,
        end_open_time=close_time,
    )
    source_fingerprint = calculate_source_fingerprint(sources) if sources else None
    if len(sources) != expected_count or any(
        candle.open_time != open_time + timedelta(minutes=index)
        for index, candle in enumerate(sources)
    ):
        return await record_incomplete_window(
            session,
            supported_market_id=supported_market_id,
            timeframe=timeframe,
            open_time=open_time,
            close_time=close_time,
            source_candle_count=len(sources),
            source_fingerprint=source_fingerprint,
            received_at=received_at,
        )
    first = sources[0]
    last = sources[-1]
    values = CandleValues(
        close_time=close_time,
        source_candle_count=expected_count,
        expected_source_candle_count=expected_count,
        source_fingerprint=source_fingerprint,
        open_price=_required_decimal(first.open_price),
        high_price=max(_required_decimal(candle.high_price) for candle in sources),
        low_price=min(_required_decimal(candle.low_price) for candle in sources),
        close_price=_required_decimal(last.close_price),
        base_volume=sum((_required_decimal(candle.base_volume) for candle in sources), Decimal("0")),
        quote_volume=sum((_required_decimal(candle.quote_volume) for candle in sources), Decimal("0")),
        trade_count=sum(_required_int(candle.trade_count) for candle in sources),
        first_trade_id=None,
        last_trade_id=None,
        provider_event_time=None,
        provider_close_time=None,
        received_at=received_at,
    )
    return await replace_derived_candle(
        session,
        supported_market_id=supported_market_id,
        timeframe=timeframe,
        open_time=open_time,
        values=values,
    )


def _required_decimal(value: Decimal | None) -> Decimal:
    if value is None:
        raise ValueError("Complete source candle was missing an exact decimal value.")
    return value


def _required_int(value: int | None) -> int:
    if value is None:
        raise ValueError("Complete source candle was missing a trade count.")
    return value
