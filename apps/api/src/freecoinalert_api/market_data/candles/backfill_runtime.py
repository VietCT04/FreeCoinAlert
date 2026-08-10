"""Concrete coordinator for the long-running canonical candle backfill."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import AsyncContextManager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from freecoinalert_api.core.config import Settings
from freecoinalert_api.db.repositories.candle_backfill_checkpoints import (
    get_checkpoint,
    mark_checkpoint_failed,
    release_backfill_lock,
    try_acquire_backfill_lock,
)
from freecoinalert_api.db.repositories.supported_markets import list_product_markets
from freecoinalert_api.db.session import get_async_engine, get_async_session_factory
from freecoinalert_api.market_data.binance_public_data import (
    BinanceArchiveCandidate,
    BinancePublicDataArchiveClient,
    plan_archive_candidates,
)
from freecoinalert_api.market_data.candles.archive_backfill import (
    BinanceCandleArchiveImporter,
)
from freecoinalert_api.market_data.candles.backfill_worker import (
    BackfillCoordinator,
    BackfillCoverageStatus,
    BackfillUnitResult,
    BackfillWorkUnit,
)
from freecoinalert_api.market_data.candles.coverage import (
    CoveragePlan,
    build_coverage_target,
    persist_coverage_plan,
    plan_coverage,
)
from freecoinalert_api.market_data.catalog import utc_now


class _BackfillLease:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await release_backfill_lock(self._connection)
        await self._connection.close()


@dataclass(frozen=True, slots=True)
class _PlannedUnit:
    market_id: UUID
    candidate: BinanceArchiveCandidate


class BinanceBackfillCoordinator(BackfillCoordinator):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = BinancePublicDataArchiveClient(
            base_url=settings.binance_public_data_base_url,
        )
        self._importer = BinanceCandleArchiveImporter(client=self._client)
        self._planned: dict[str, _PlannedUnit] = {}

    async def get_coverage_status(self) -> BackfillCoverageStatus:
        now = utc_now()
        plans: list[CoveragePlan] = []
        async with get_async_session_factory()() as session:
            async with session.begin():
                markets = [
                    market
                    for market in await list_product_markets(session)
                    if market.product_enabled
                ]
                for market in markets:
                    plans.append(
                        await self._refresh_market_coverage(
                            session,
                            market_id=market.id,
                            symbol=market.symbol,
                            now=now,
                        )
                    )

        if not plans:
            return BackfillCoverageStatus(
                status="degraded",
                available_start=None,
                available_end=None,
                target_start=None,
                target_end=None,
                coverage_percent=None,
                last_success_at=None,
                last_error_category="market_catalog_empty",
            )

        coverage_percent = min(
            (
                Decimal(plan.statistics.complete_count)
                * Decimal("100")
                / Decimal(max(plan.statistics.expected_count, 1))
            )
            for plan in plans
        )
        available_starts = [
            plan.statistics.first_open_time
            for plan in plans
            if plan.statistics.first_open_time is not None
        ]
        available_ends = [
            plan.statistics.last_close_time
            for plan in plans
            if plan.statistics.last_close_time is not None
        ]
        complete = all(plan.is_complete for plan in plans)
        return BackfillCoverageStatus(
            status="ready" if complete else "backfilling",
            available_start=min(available_starts) if available_starts else None,
            available_end=max(available_ends) if available_ends else None,
            target_start=min(plan.target.target_start for plan in plans),
            target_end=max(plan.target.target_end for plan in plans),
            coverage_percent=coverage_percent,
            last_success_at=now if complete else None,
            last_error_category=None,
        )

    async def try_acquire_owner(self) -> AsyncContextManager[None] | None:
        connection = await get_async_engine().connect()
        if not await try_acquire_backfill_lock(connection):
            await connection.close()
            return None
        return _BackfillLease(connection)

    async def next_work_unit(self) -> BackfillWorkUnit | None:
        now = utc_now()
        async with get_async_session_factory()() as session:
            markets = [
                market
                for market in await list_product_markets(session)
                if market.product_enabled
            ]
            for market in markets:
                target = build_coverage_target(
                    supported_market_id=market.id,
                    symbol=market.symbol,
                    timeframe="1m",
                    now=now,
                    target_days=self._settings.candle_backfill_target_days,
                )
                plan = await plan_coverage(session, target=target)
                for missing_range in plan.missing_ranges:
                    candidates = plan_archive_candidates(
                        symbol=market.symbol,
                        start_open_time=missing_range.start_open_time,
                        end_open_time=missing_range.end_open_time,
                        now=target.target_end,
                    )
                    for candidate in candidates:
                        if await self._candidate_is_complete(session, candidate):
                            continue
                        self._planned[candidate.primary.archive_key] = _PlannedUnit(
                            market_id=market.id,
                            candidate=candidate,
                        )
                        descriptor = candidate.primary
                        return BackfillWorkUnit(
                            symbol=descriptor.symbol,
                            archive_key=descriptor.archive_key,
                            period_start=descriptor.period_start,
                            period_end=descriptor.period_end,
                            archive_granularity=descriptor.granularity,
                        )
        return None

    async def process_work_unit(
        self,
        work_unit: BackfillWorkUnit,
        *,
        chunk_pause_seconds: float,
    ) -> BackfillUnitResult:
        del chunk_pause_seconds
        planned = self._planned.pop(work_unit.archive_key, None)
        if planned is None:
            raise RuntimeError("Backfill work unit was not retained by the coordinator.")
        result = await self._importer.import_candidate(
            candidate=planned.candidate,
            supported_market_id=planned.market_id,
        )
        await self._refresh_market_by_id(planned.market_id)
        return BackfillUnitResult(
            state="complete" if result.status == "complete" else "committed",
            source_rows_written=result.committed_row_count,
            source_rows_unchanged=0,
            source_rows_corrected=0,
            derived_rows_written=0,
            next_open_time=result.next_open_time,
        )

    async def defer_work_unit(
        self,
        work_unit: BackfillWorkUnit,
        *,
        failure_category: str,
    ) -> None:
        planned = self._planned.pop(work_unit.archive_key, None)
        if planned is None:
            return
        async with get_async_session_factory()() as session:
            async with session.begin():
                checkpoint = await get_checkpoint(
                    session,
                    archive_key=work_unit.archive_key,
                    for_update=True,
                )
                if checkpoint is not None:
                    await mark_checkpoint_failed(
                        session,
                        checkpoint=checkpoint,
                        category=failure_category,
                    )

    async def _refresh_market_by_id(self, market_id: UUID) -> None:
        async with get_async_session_factory()() as session:
            async with session.begin():
                market = next(
                    (
                        item
                        for item in await list_product_markets(session)
                        if item.id == market_id
                    ),
                    None,
                )
                if market is not None:
                    await self._refresh_market_coverage(
                        session,
                        market_id=market.id,
                        symbol=market.symbol,
                        now=utc_now(),
                    )

    async def _refresh_market_coverage(
        self,
        session: AsyncSession,
        *,
        market_id: UUID,
        symbol: str,
        now: datetime,
    ) -> CoveragePlan:
        one_minute_plan: CoveragePlan | None = None
        for timeframe in ("1m", "1h", "4h"):
            target = build_coverage_target(
                supported_market_id=market_id,
                symbol=symbol,
                timeframe=timeframe,
                now=now,
                target_days=self._settings.candle_backfill_target_days,
            )
            current_plan = await plan_coverage(session, target=target)
            await persist_coverage_plan(
                session,
                plan=current_plan,
                verified_at=now,
            )
            if timeframe == "1m":
                one_minute_plan = current_plan
        if one_minute_plan is None:
            raise RuntimeError("The one-minute coverage plan was not created.")
        return one_minute_plan

    @staticmethod
    async def _candidate_is_complete(
        session: AsyncSession,
        candidate: BinanceArchiveCandidate,
    ) -> bool:
        primary = await get_checkpoint(
            session,
            archive_key=candidate.primary.archive_key,
        )
        if primary is not None and primary.status == "complete":
            return True
        if not candidate.daily_fallbacks:
            return False
        for fallback in candidate.daily_fallbacks:
            checkpoint = await get_checkpoint(
                session,
                archive_key=fallback.archive_key,
            )
            if checkpoint is None or checkpoint.status != "complete":
                return False
        return True


def build_backfill_coordinator(settings: Settings) -> BinanceBackfillCoordinator:
    return BinanceBackfillCoordinator(settings)
