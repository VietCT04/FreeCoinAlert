import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.repositories.candle_operations import (
    mark_candle_reconciliation_state,
)
from freecoinalert_api.db.repositories.market_candles import find_missing_one_minute_ranges
from freecoinalert_api.db.repositories.supported_markets import list_product_markets
from freecoinalert_api.db.session import get_async_engine, get_async_session_factory
from freecoinalert_api.market_data.binance_rest import (
    MAX_KLINE_PAGE_MINUTES,
    BinanceMetadataError,
    BinancePublicMarketDataClient,
)
from freecoinalert_api.market_data.candles.ingestion import CandleIngestionService
from freecoinalert_api.market_data.catalog import is_market_ready, utc_now
from freecoinalert_api.market_data.events import CanonicalOneMinuteCandleInput
from freecoinalert_api.market_data.state import SINGLETON_LOCK_KEY

logger = logging.getLogger(__name__)

MAX_REST_REPAIR_MINUTES_PER_SYMBOL = 7 * 24 * 60


@dataclass(frozen=True, slots=True)
class CandleReconciliationRange:
    """Explicit canonical gap supplied by a coverage planner.

    Archive ingestion and coverage planning own how a range is discovered.
    This boundary only fetches bounded REST pages and sends normalized inputs
    through ``CandleIngestionService``.
    """

    supported_market_id: UUID
    symbol: str
    start_open_time: datetime
    end_open_time: datetime

    def __post_init__(self) -> None:
        if self.start_open_time.tzinfo is None or self.end_open_time.tzinfo is None:
            raise ValueError("Candle reconciliation ranges must be timezone-aware.")
        if self.start_open_time >= self.end_open_time:
            raise ValueError("Candle reconciliation range must be non-empty.")
        if (
            self.start_open_time.second
            or self.start_open_time.microsecond
            or self.end_open_time.second
            or self.end_open_time.microsecond
        ):
            raise ValueError("Candle reconciliation ranges must align to UTC minutes.")


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

    connection = await _acquire_singleton_lock() if acquire_lock else None
    if acquire_lock and connection is None:
        return 0

    try:
        now = utc_now().replace(second=0, microsecond=0)
        start = now - timedelta(hours=hours)
        ranges = await _plan_recent_ranges(start_open_time=start, end_open_time=now)
        return await reconcile_ranges(
            ranges,
            kind=kind,
            acquire_lock=False,
            base_url=settings.binance_spot_base_url,
        )
    finally:
        if connection is not None:
            await connection.close()


async def reconcile_ranges(
    ranges: list[CandleReconciliationRange],
    *,
    kind: str = "recent_reconciliation",
    acquire_lock: bool = True,
    base_url: str | None = None,
) -> int | None:
    """Reconcile explicit canonical gaps through bounded Binance REST pages.

    Ranges are processed oldest-first, one market at a time, and one request
    at a time. A coverage owner can pass archive-unavailable or recent gaps
    without this module discovering archive files or maintaining checkpoints.
    """

    connection = await _acquire_singleton_lock() if acquire_lock else None
    if acquire_lock and connection is None:
        return 0

    try:
        settings = get_settings()
        client = BinancePublicMarketDataClient(
            base_url=base_url or settings.binance_spot_base_url
        )
        ingestion = CandleIngestionService()
        repaired = 0
        grouped: dict[UUID, list[CandleReconciliationRange]] = defaultdict(list)
        for reconciliation_range in ranges:
            grouped[reconciliation_range.supported_market_id].append(reconciliation_range)

        for market_ranges in grouped.values():
            ordered_ranges = sorted(market_ranges, key=lambda item: item.start_open_time)
            remaining_ranges = list(ordered_ranges)
            allowed_minutes = MAX_REST_REPAIR_MINUTES_PER_SYMBOL
            last_reconciled_through: datetime | None = None

            while remaining_ranges and allowed_minutes > 0:
                reconciliation_range = remaining_ranges.pop(0)
                range_minutes = _range_minutes(reconciliation_range)
                page_end = min(
                    reconciliation_range.end_open_time,
                    reconciliation_range.start_open_time
                    + timedelta(minutes=min(range_minutes, allowed_minutes)),
                )
                if page_end < reconciliation_range.end_open_time:
                    remaining_ranges.insert(
                        0,
                        CandleReconciliationRange(
                            supported_market_id=reconciliation_range.supported_market_id,
                            symbol=reconciliation_range.symbol,
                            start_open_time=page_end,
                            end_open_time=reconciliation_range.end_open_time,
                        ),
                    )

                page_start = reconciliation_range.start_open_time
                while page_start < page_end:
                    current_page_end = min(
                        page_start + timedelta(minutes=MAX_KLINE_PAGE_MINUTES),
                        page_end,
                    )
                    try:
                        klines = await client.get_spot_klines(
                            symbol=reconciliation_range.symbol,
                            start_open_time=page_start,
                            end_open_time=current_page_end,
                        )
                    except BinanceMetadataError as error:
                        remaining_ranges.insert(
                            0,
                            CandleReconciliationRange(
                                supported_market_id=reconciliation_range.supported_market_id,
                                symbol=reconciliation_range.symbol,
                                start_open_time=page_start,
                                end_open_time=page_end,
                            ),
                        )
                        await _record_reconciliation_state(
                            supported_market_id=reconciliation_range.supported_market_id,
                            status="error",
                            unresolved_gap_count=len(remaining_ranges),
                            status_reason="provider_unavailable",
                            last_reconciled_through=last_reconciled_through,
                        )
                        logger.warning(
                            "market.candle.reconciliation_deferred symbol=%s "
                            "reason=provider_unavailable category=%s remaining_gap=%s",
                            reconciliation_range.symbol,
                            error.category,
                            _remaining_minutes(remaining_ranges),
                        )
                        logger.warning(
                            "market.candle.reconciliation_failed category=%s",
                            error.category,
                        )
                        return 1

                    if not klines:
                        remaining_ranges.insert(
                            0,
                            CandleReconciliationRange(
                                supported_market_id=reconciliation_range.supported_market_id,
                                symbol=reconciliation_range.symbol,
                                start_open_time=page_start,
                                end_open_time=current_page_end,
                            ),
                        )
                        logger.warning(
                            "market.candle.reconciliation_deferred symbol=%s "
                            "reason=empty_provider_response remaining_gap=%s",
                            reconciliation_range.symbol,
                            _remaining_minutes(remaining_ranges),
                        )
                        page_start = page_end
                        break

                    received_at = utc_now()
                    inputs = [
                        CanonicalOneMinuteCandleInput(
                            exchange="binance",
                            market_type="spot",
                            supported_market_id=reconciliation_range.supported_market_id,
                            symbol=reconciliation_range.symbol,
                            timeframe="1m",
                            open_time=kline.open_time,
                            close_time=kline.close_time,
                            provider_close_time=kline.provider_close_time,
                            open_price=kline.open_price,
                            high_price=kline.high_price,
                            low_price=kline.low_price,
                            close_price=kline.close_price,
                            base_volume=kline.base_volume,
                            quote_volume=kline.quote_volume,
                            trade_count=kline.trade_count,
                            first_trade_id=kline.first_trade_id,
                            last_trade_id=kline.last_trade_id,
                            provider_event_time=None,
                            received_at=received_at,
                        )
                        for kline in klines
                    ]
                    repaired += await ingestion.persist_canonical_candles(inputs)
                    logger.info(
                        "market.candle.reconciliation_page symbol=%s start=%s end=%s row_count=%s",
                        reconciliation_range.symbol,
                        page_start,
                        current_page_end,
                        len(klines),
                    )
                    last_reconciled_through = current_page_end
                    page_start = current_page_end

                if page_start >= page_end:
                    processed_minutes = _minutes_between(
                        reconciliation_range.start_open_time,
                        page_end,
                    )
                    allowed_minutes = max(0, allowed_minutes - processed_minutes)

            status = "gapped" if remaining_ranges else "live"
            unresolved_gap_count = len(remaining_ranges)
            await _record_reconciliation_state(
                supported_market_id=ordered_ranges[0].supported_market_id,
                status=status,
                unresolved_gap_count=unresolved_gap_count,
                status_reason="reconciliation_bound" if remaining_ranges else None,
                last_reconciled_through=last_reconciled_through,
            )
            if remaining_ranges:
                logger.info(
                    "market.candle.reconciliation_deferred symbol=%s "
                    "reason=pass_bound remaining_gap=%s",
                    ordered_ranges[0].symbol,
                    _remaining_minutes(remaining_ranges),
                )

        logger.info(
            "market.candle.reconciliation_completed kind=%s repaired=%s",
            kind,
            repaired,
        )
        return None
    finally:
        if connection is not None:
            await connection.close()


async def _plan_recent_ranges(
    *,
    start_open_time: datetime,
    end_open_time: datetime,
) -> list[CandleReconciliationRange]:
    async with get_async_session_factory()() as session:
        markets = [
            market
            for market in await list_product_markets(session)
            if is_market_ready(market, current_time=utc_now(), max_age_seconds=86400)
        ]
        planned: list[CandleReconciliationRange] = []
        for market in markets:
            gaps = await find_missing_one_minute_ranges(
                session,
                supported_market_id=market.id,
                start_open_time=start_open_time,
                end_open_time=end_open_time,
            )
            planned.extend(
                CandleReconciliationRange(
                    supported_market_id=market.id,
                    symbol=market.symbol,
                    start_open_time=gap.start_open_time,
                    end_open_time=gap.end_open_time,
                )
                for gap in gaps
            )
        return planned


async def _record_reconciliation_state(
    *,
    supported_market_id: UUID,
    status: str,
    unresolved_gap_count: int,
    status_reason: str | None,
    last_reconciled_through: datetime | None,
) -> None:
    async with get_async_session_factory()() as session:
        async with session.begin():
            await mark_candle_reconciliation_state(
                session,
                supported_market_id=supported_market_id,
                status=status,
                unresolved_gap_count=unresolved_gap_count,
                status_reason=status_reason,
                last_reconciled_through=last_reconciled_through,
            )


async def _acquire_singleton_lock() -> AsyncConnection | None:
    connection = await get_async_engine().connect()
    acquired = await connection.scalar(
        text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
        {"lock_key": SINGLETON_LOCK_KEY},
    )
    if acquired:
        return connection
    logger.info("market.candle.reconciliation_skipped category=market_stream_already_running")
    await connection.close()
    return None


def _range_minutes(reconciliation_range: CandleReconciliationRange) -> int:
    return _minutes_between(
        reconciliation_range.start_open_time,
        reconciliation_range.end_open_time,
    )


def _minutes_between(start_open_time: datetime, end_open_time: datetime) -> int:
    return int((end_open_time - start_open_time) / timedelta(minutes=1))


def _remaining_minutes(ranges: list[CandleReconciliationRange]) -> int:
    return sum(_range_minutes(reconciliation_range) for reconciliation_range in ranges)


def main() -> None:
    settings = get_settings()
    raise SystemExit(
        asyncio.run(
            reconcile_recent(
                hours=settings.candle_reconciliation_lookback_hours,
                kind="reconciliation",
            )
        )
    )


if __name__ == "__main__":
    main()
