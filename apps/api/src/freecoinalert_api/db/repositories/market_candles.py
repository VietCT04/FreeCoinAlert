import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.market_candle import MarketCandle


TIMEFRAME_SOURCE_COUNTS = {"1m": 1, "1h": 60, "4h": 240}
TIMEFRAME_DELTAS = {
    "1m": timedelta(minutes=1),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}


@dataclass(frozen=True)
class CandleValues:
    close_time: datetime
    source_candle_count: int
    expected_source_candle_count: int
    source_fingerprint: str | None
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    close_price: Decimal | None
    base_volume: Decimal | None
    quote_volume: Decimal | None
    trade_count: int | None
    first_trade_id: int | None
    last_trade_id: int | None
    provider_event_time: datetime | None
    provider_close_time: datetime | None
    received_at: datetime


@dataclass(frozen=True)
class MissingCandleRange:
    start_open_time: datetime
    end_open_time: datetime


@dataclass(frozen=True)
class CandleCoverageStatistics:
    timeframe: str
    requested_start: datetime
    requested_end: datetime
    complete_count: int
    first_open_time: datetime | None
    last_close_time: datetime | None
    has_no_gaps: bool

    @property
    def expected_count(self) -> int:
        delta = timedelta(minutes=1)
        if self.timeframe == "1h":
            delta = timedelta(hours=1)
        elif self.timeframe == "4h":
            delta = timedelta(hours=4)
        return int((self.requested_end - self.requested_start) / delta)

    @property
    def is_complete(self) -> bool:
        return (
            self.complete_count == self.expected_count
            and self.first_open_time == self.requested_start
            and self.last_close_time == self.requested_end
            and self.has_no_gaps
        )


def calculate_source_fingerprint(candles: Sequence[MarketCandle]) -> str:
    source_identity = "|".join(f"{candle.id}:{candle.revision}" for candle in candles)
    return hashlib.sha256(source_identity.encode("ascii")).hexdigest()


def _validate_utc_range(start_open_time: datetime, end_open_time: datetime) -> None:
    if start_open_time.tzinfo is None or end_open_time.tzinfo is None:
        raise ValueError("Candle ranges must use timezone-aware UTC timestamps.")

    if start_open_time >= end_open_time:
        raise ValueError("Candle range end must be later than its start.")

    if start_open_time.second or start_open_time.microsecond:
        raise ValueError("Candle range start must align with a UTC minute boundary.")

    if end_open_time.second or end_open_time.microsecond:
        raise ValueError("Candle range end must align with a UTC minute boundary.")


def _timeframe_delta(timeframe: str) -> timedelta:
    try:
        return TIMEFRAME_DELTAS[timeframe]
    except KeyError as error:
        raise ValueError("Unsupported candle timeframe.") from error


def _canonical_values_match(candle: MarketCandle, values: CandleValues) -> bool:
    return (
        candle.close_time == values.close_time
        and candle.source_candle_count == values.source_candle_count
        and candle.expected_source_candle_count == values.expected_source_candle_count
        and candle.source_fingerprint == values.source_fingerprint
        and candle.open_price == values.open_price
        and candle.high_price == values.high_price
        and candle.low_price == values.low_price
        and candle.close_price == values.close_price
        and candle.base_volume == values.base_volume
        and candle.quote_volume == values.quote_volume
        and candle.trade_count == values.trade_count
        and candle.first_trade_id == values.first_trade_id
        and candle.last_trade_id == values.last_trade_id
        and candle.provider_close_time == values.provider_close_time
    )


def _validate_complete_values(values: CandleValues) -> None:
    decimal_values = (
        values.open_price,
        values.high_price,
        values.low_price,
        values.close_price,
        values.base_volume,
        values.quote_volume,
    )

    if any(value is None or not isinstance(value, Decimal) for value in decimal_values):
        raise ValueError("Complete candle values must use Decimal values.")

    if any(not value.is_finite() for value in decimal_values if value is not None):
        raise ValueError("Complete candle values must be finite.")

    if values.source_candle_count != values.expected_source_candle_count:
        raise ValueError("A complete candle must contain every expected source candle.")


def _new_complete_candle(
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    open_time: datetime,
    source_kind: str,
    values: CandleValues,
    revision: int,
    supersedes_candle_id: uuid.UUID | None,
) -> MarketCandle:
    _validate_complete_values(values)

    return MarketCandle(
        supported_market_id=supported_market_id,
        timeframe=timeframe,
        open_time=open_time,
        close_time=values.close_time,
        source_kind=source_kind,
        status="complete",
        status_reason=None,
        revision=revision,
        is_current=True,
        supersedes_candle_id=supersedes_candle_id,
        source_candle_count=values.source_candle_count,
        expected_source_candle_count=values.expected_source_candle_count,
        source_fingerprint=values.source_fingerprint,
        open_price=values.open_price,
        high_price=values.high_price,
        low_price=values.low_price,
        close_price=values.close_price,
        base_volume=values.base_volume,
        quote_volume=values.quote_volume,
        trade_count=values.trade_count,
        first_trade_id=values.first_trade_id,
        last_trade_id=values.last_trade_id,
        provider_event_time=values.provider_event_time,
        provider_close_time=values.provider_close_time,
        received_at=values.received_at,
    )


async def get_current_candle(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    open_time: datetime,
) -> MarketCandle | None:
    statement = select(MarketCandle).where(
        MarketCandle.supported_market_id == supported_market_id,
        MarketCandle.timeframe == timeframe,
        MarketCandle.open_time == open_time,
        MarketCandle.is_current.is_(True),
    )
    return await session.scalar(statement)


async def get_current_candle_for_update(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    open_time: datetime,
) -> MarketCandle | None:
    statement = (
        select(MarketCandle)
        .where(
            MarketCandle.supported_market_id == supported_market_id,
            MarketCandle.timeframe == timeframe,
            MarketCandle.open_time == open_time,
            MarketCandle.is_current.is_(True),
        )
        .with_for_update()
    )
    return await session.scalar(statement)


async def _replace_current_complete_candle(
    session: AsyncSession,
    *,
    current: MarketCandle,
    values: CandleValues,
) -> MarketCandle:
    if current.status != "complete":
        raise ValueError("Only a current complete candle can be superseded by a revision.")

    current.status = "superseded"
    current.is_current = False
    replacement = _new_complete_candle(
        supported_market_id=current.supported_market_id,
        timeframe=current.timeframe,
        open_time=current.open_time,
        source_kind=current.source_kind,
        values=values,
        revision=current.revision + 1,
        supersedes_candle_id=current.id,
    )
    session.add(replacement)
    await session.flush()
    return replacement


async def upsert_closed_source_candle(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    open_time: datetime,
    values: CandleValues,
) -> MarketCandle:
    if values.expected_source_candle_count != TIMEFRAME_SOURCE_COUNTS["1m"]:
        raise ValueError("A canonical one-minute candle must expect one source candle.")

    current = await get_current_candle_for_update(
        session,
        supported_market_id=supported_market_id,
        timeframe="1m",
        open_time=open_time,
    )

    if current is None:
        candle = _new_complete_candle(
            supported_market_id=supported_market_id,
            timeframe="1m",
            open_time=open_time,
            source_kind="binance_kline",
            values=values,
            revision=1,
            supersedes_candle_id=None,
        )
        session.add(candle)
        await session.flush()
        return candle

    if _canonical_values_match(current, values):
        return current

    return await _replace_current_complete_candle(
        session,
        current=current,
        values=values,
    )


async def replace_derived_candle(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    open_time: datetime,
    values: CandleValues,
) -> MarketCandle:
    if timeframe not in {"1h", "4h"}:
        raise ValueError("Derived candles are limited to 1h and 4h.")

    if values.expected_source_candle_count != TIMEFRAME_SOURCE_COUNTS[timeframe]:
        raise ValueError("Derived candle source count does not match its timeframe.")

    current = await get_current_candle_for_update(
        session,
        supported_market_id=supported_market_id,
        timeframe=timeframe,
        open_time=open_time,
    )

    if current is None:
        candle = _new_complete_candle(
            supported_market_id=supported_market_id,
            timeframe=timeframe,
            open_time=open_time,
            source_kind="aggregate_1m",
            values=values,
            revision=1,
            supersedes_candle_id=None,
        )
        session.add(candle)
        await session.flush()
        return candle

    if _canonical_values_match(current, values):
        return current

    if current.status in {"incomplete", "invalid"}:
        _apply_in_place_completion(current, values)
        await session.flush()
        return current

    return await _replace_current_complete_candle(
        session,
        current=current,
        values=values,
    )


def _apply_in_place_completion(candle: MarketCandle, values: CandleValues) -> None:
    candle.close_time = values.close_time
    candle.status = "complete"
    candle.status_reason = None
    candle.source_candle_count = values.source_candle_count
    candle.expected_source_candle_count = values.expected_source_candle_count
    candle.source_fingerprint = values.source_fingerprint
    candle.open_price = values.open_price
    candle.high_price = values.high_price
    candle.low_price = values.low_price
    candle.close_price = values.close_price
    candle.base_volume = values.base_volume
    candle.quote_volume = values.quote_volume
    candle.trade_count = values.trade_count
    candle.first_trade_id = values.first_trade_id
    candle.last_trade_id = values.last_trade_id
    candle.provider_event_time = values.provider_event_time
    candle.provider_close_time = values.provider_close_time
    candle.received_at = values.received_at


async def _record_noncomplete_window(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    open_time: datetime,
    close_time: datetime,
    status: str,
    status_reason: str,
    source_candle_count: int,
    source_fingerprint: str | None,
    received_at: datetime,
) -> MarketCandle:
    current = await get_current_candle_for_update(
        session,
        supported_market_id=supported_market_id,
        timeframe=timeframe,
        open_time=open_time,
    )

    if current is not None and current.status == "complete":
        return current

    expected_source_candle_count = TIMEFRAME_SOURCE_COUNTS[timeframe]
    if current is None:
        source_kind = "binance_kline" if timeframe == "1m" else "aggregate_1m"
        current = MarketCandle(
            supported_market_id=supported_market_id,
            timeframe=timeframe,
            open_time=open_time,
            close_time=close_time,
            source_kind=source_kind,
            status=status,
            status_reason=status_reason,
            revision=1,
            is_current=True,
            supersedes_candle_id=None,
            source_candle_count=source_candle_count,
            expected_source_candle_count=expected_source_candle_count,
            source_fingerprint=source_fingerprint,
            open_price=None,
            high_price=None,
            low_price=None,
            close_price=None,
            base_volume=None,
            quote_volume=None,
            trade_count=None,
            first_trade_id=None,
            last_trade_id=None,
            provider_event_time=None,
            provider_close_time=None,
            received_at=received_at,
        )
        session.add(current)
    else:
        current.close_time = close_time
        current.status = status
        current.status_reason = status_reason
        current.source_candle_count = source_candle_count
        current.source_fingerprint = source_fingerprint
        current.received_at = received_at

    await session.flush()
    return current


async def record_incomplete_window(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    open_time: datetime,
    close_time: datetime,
    source_candle_count: int,
    source_fingerprint: str | None,
    received_at: datetime,
) -> MarketCandle:
    if timeframe not in {"1h", "4h"}:
        raise ValueError("Only derived windows can be incomplete.")

    return await _record_noncomplete_window(
        session,
        supported_market_id=supported_market_id,
        timeframe=timeframe,
        open_time=open_time,
        close_time=close_time,
        status="incomplete",
        status_reason="missing_source_candles",
        source_candle_count=source_candle_count,
        source_fingerprint=source_fingerprint,
        received_at=received_at,
    )


async def record_invalid_window(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    open_time: datetime,
    close_time: datetime,
    status_reason: str,
    source_candle_count: int,
    source_fingerprint: str | None,
    received_at: datetime,
) -> MarketCandle:
    if timeframe not in TIMEFRAME_SOURCE_COUNTS:
        raise ValueError("Unsupported candle timeframe.")

    return await _record_noncomplete_window(
        session,
        supported_market_id=supported_market_id,
        timeframe=timeframe,
        open_time=open_time,
        close_time=close_time,
        status="invalid",
        status_reason=status_reason,
        source_candle_count=source_candle_count,
        source_fingerprint=source_fingerprint,
        received_at=received_at,
    )


async def list_complete_candles(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    start_open_time: datetime,
    end_open_time: datetime,
    limit: int,
) -> Sequence[MarketCandle]:
    _validate_utc_range(start_open_time, end_open_time)
    statement = (
        select(MarketCandle)
        .where(
            MarketCandle.supported_market_id == supported_market_id,
            MarketCandle.timeframe == timeframe,
            MarketCandle.is_current.is_(True),
            MarketCandle.status == "complete",
            MarketCandle.open_time >= start_open_time,
            MarketCandle.open_time < end_open_time,
        )
        .order_by(MarketCandle.open_time.desc())
        .limit(limit)
    )
    return (await session.scalars(statement)).all()


async def list_complete_candles_ascending(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    start_open_time: datetime,
    end_open_time: datetime,
    limit: int,
) -> Sequence[MarketCandle]:
    _validate_utc_range(start_open_time, end_open_time)
    statement = (
        select(MarketCandle)
        .where(
            MarketCandle.supported_market_id == supported_market_id,
            MarketCandle.timeframe == timeframe,
            MarketCandle.is_current.is_(True),
            MarketCandle.status == "complete",
            MarketCandle.open_time >= start_open_time,
            MarketCandle.open_time < end_open_time,
        )
        .order_by(MarketCandle.open_time.asc())
        .limit(limit)
    )
    return (await session.scalars(statement)).all()


async def list_current_source_window(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    start_open_time: datetime,
    end_open_time: datetime,
) -> Sequence[MarketCandle]:
    _validate_utc_range(start_open_time, end_open_time)
    return await list_complete_candles_ascending(
        session,
        supported_market_id=supported_market_id,
        timeframe="1m",
        start_open_time=start_open_time,
        end_open_time=end_open_time,
        limit=TIMEFRAME_SOURCE_COUNTS["4h"],
    )


async def find_missing_one_minute_ranges(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    start_open_time: datetime,
    end_open_time: datetime,
) -> Sequence[MissingCandleRange]:
    return await find_missing_candle_ranges(
        session,
        supported_market_id=supported_market_id,
        timeframe="1m",
        start_open_time=start_open_time,
        end_open_time=end_open_time,
    )


async def get_complete_candle_coverage(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    start_open_time: datetime,
    end_open_time: datetime,
) -> CandleCoverageStatistics:
    _validate_utc_range(start_open_time, end_open_time)
    delta_seconds = _timeframe_delta(timeframe).total_seconds()
    row = (
        await session.execute(
            text(
                """
                WITH ordered AS (
                    SELECT
                        open_time,
                        close_time,
                        LAG(open_time) OVER (ORDER BY open_time) AS previous_open_time
                    FROM market_candles
                    WHERE supported_market_id = :supported_market_id
                      AND timeframe = :timeframe
                      AND is_current = true
                      AND status = 'complete'
                      AND open_time >= :start_open_time
                      AND open_time < :end_open_time
                )
                SELECT
                    COUNT(*) AS complete_count,
                    MIN(open_time) AS first_open_time,
                    MAX(close_time) AS last_close_time,
                    COALESCE(
                        BOOL_AND(
                            previous_open_time IS NULL
                            OR open_time = previous_open_time
                                + (:delta_seconds * INTERVAL '1 second')
                        ),
                        true
                    ) AS has_no_gaps
                FROM ordered
                """
            ),
            {
                "supported_market_id": supported_market_id,
                "timeframe": timeframe,
                "start_open_time": start_open_time.astimezone(UTC),
                "end_open_time": end_open_time.astimezone(UTC),
                "delta_seconds": int(delta_seconds),
            },
        )
    ).one()
    return CandleCoverageStatistics(
        timeframe=timeframe,
        requested_start=start_open_time.astimezone(UTC),
        requested_end=end_open_time.astimezone(UTC),
        complete_count=int(row.complete_count),
        first_open_time=(
            None if row.first_open_time is None else row.first_open_time.astimezone(UTC)
        ),
        last_close_time=(
            None if row.last_close_time is None else row.last_close_time.astimezone(UTC)
        ),
        has_no_gaps=bool(row.has_no_gaps),
    )


async def get_newest_contiguous_candle_range(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    start_open_time: datetime,
    end_open_time: datetime,
) -> tuple[datetime, datetime] | None:
    """Find the newest complete run in a bounded range with DB-side windowing."""

    _validate_utc_range(start_open_time, end_open_time)
    delta_seconds = _timeframe_delta(timeframe).total_seconds()
    row = (
        await session.execute(
            text(
                """
                WITH descending AS (
                    SELECT
                        open_time,
                        close_time,
                        LAG(open_time) OVER (ORDER BY open_time DESC) AS later_open_time
                    FROM market_candles
                    WHERE supported_market_id = :supported_market_id
                      AND timeframe = :timeframe
                      AND is_current = true
                      AND status = 'complete'
                      AND open_time >= :start_open_time
                      AND open_time < :end_open_time
                ),
                marked AS (
                    SELECT
                        open_time,
                        close_time,
                        SUM(
                            CASE
                                WHEN later_open_time IS NOT NULL
                                 AND later_open_time <> open_time
                                    + (:delta_seconds * INTERVAL '1 second')
                                THEN 1
                                ELSE 0
                            END
                        ) OVER (ORDER BY open_time DESC ROWS UNBOUNDED PRECEDING) AS gap_group
                    FROM descending
                )
                SELECT MIN(open_time) AS contiguous_start,
                       MAX(close_time) AS contiguous_end
                FROM marked
                WHERE gap_group = 0
                """
            ),
            {
                "supported_market_id": supported_market_id,
                "timeframe": timeframe,
                "start_open_time": start_open_time.astimezone(UTC),
                "end_open_time": end_open_time.astimezone(UTC),
                "delta_seconds": int(delta_seconds),
            },
        )
    ).one()
    if row.contiguous_start is None or row.contiguous_end is None:
        return None
    return row.contiguous_start.astimezone(UTC), row.contiguous_end.astimezone(UTC)


async def find_missing_candle_ranges(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    timeframe: str,
    start_open_time: datetime,
    end_open_time: datetime,
) -> Sequence[MissingCandleRange]:
    """Return gaps using indexed DB-side windowing, without loading the range."""

    _validate_utc_range(start_open_time, end_open_time)
    delta_seconds = _timeframe_delta(timeframe).total_seconds()
    rows = (
        await session.execute(
            text(
                """
                WITH ordered AS (
                    SELECT
                        open_time,
                        LEAD(open_time) OVER (ORDER BY open_time) AS next_open_time
                    FROM market_candles
                    WHERE supported_market_id = :supported_market_id
                      AND timeframe = :timeframe
                      AND is_current = true
                      AND status = 'complete'
                      AND open_time >= :start_open_time
                      AND open_time < :end_open_time
                ),
                bounds AS (
                    SELECT MIN(open_time) AS first_open_time,
                           MAX(open_time) AS last_open_time
                    FROM ordered
                ),
                gaps AS (
                    SELECT :start_open_time AS gap_start,
                           :end_open_time AS gap_end
                    FROM bounds
                    WHERE first_open_time IS NULL

                    UNION ALL

                    SELECT :start_open_time AS gap_start,
                           first_open_time AS gap_end
                    FROM bounds
                    WHERE first_open_time > :start_open_time

                    UNION ALL

                    SELECT open_time + (:delta_seconds * INTERVAL '1 second') AS gap_start,
                           next_open_time AS gap_end
                    FROM ordered
                    WHERE next_open_time > open_time
                        + (:delta_seconds * INTERVAL '1 second')

                    UNION ALL

                    SELECT last_open_time + (:delta_seconds * INTERVAL '1 second') AS gap_start,
                           :end_open_time AS gap_end
                    FROM bounds
                    WHERE last_open_time IS NOT NULL
                      AND last_open_time + (:delta_seconds * INTERVAL '1 second')
                          < :end_open_time
                )
                SELECT gap_start, gap_end
                FROM gaps
                WHERE gap_end > gap_start
                ORDER BY gap_start
                """
            ),
            {
                "supported_market_id": supported_market_id,
                "timeframe": timeframe,
                "start_open_time": start_open_time.astimezone(UTC),
                "end_open_time": end_open_time.astimezone(UTC),
                "delta_seconds": int(delta_seconds),
            },
        )
    ).all()
    return tuple(
        MissingCandleRange(
            start_open_time=row.gap_start.astimezone(UTC),
            end_open_time=row.gap_end.astimezone(UTC),
        )
        for row in rows
    )


async def find_changed_source_windows(
    session: AsyncSession,
    *,
    supported_market_id: uuid.UUID,
    source_open_time: datetime,
) -> Sequence[MarketCandle]:
    if source_open_time.tzinfo is None:
        raise ValueError("Source time must be timezone-aware UTC.")

    source_open_time = source_open_time.astimezone(UTC).replace(second=0, microsecond=0)
    hour_open_time = source_open_time.replace(minute=0)
    four_hour_open_time = hour_open_time.replace(
        hour=hour_open_time.hour - hour_open_time.hour % 4
    )
    statement = (
        select(MarketCandle)
        .where(
            MarketCandle.supported_market_id == supported_market_id,
            MarketCandle.is_current.is_(True),
            (
                (MarketCandle.timeframe == "1h")
                & (MarketCandle.open_time == hour_open_time)
            )
            | (
                (MarketCandle.timeframe == "4h")
                & (MarketCandle.open_time == four_hour_open_time)
            ),
        )
        .order_by(MarketCandle.timeframe, MarketCandle.open_time)
    )
    return (await session.scalars(statement)).all()


async def delete_candle_revisions_before(
    session: AsyncSession,
    *,
    cutoff: datetime,
) -> int:
    if cutoff.tzinfo is None:
        raise ValueError("Candle retention cutoff must be timezone-aware UTC.")

    result = await session.execute(
        delete(MarketCandle).where(MarketCandle.close_time < cutoff.astimezone(UTC))
    )
    return result.rowcount or 0
