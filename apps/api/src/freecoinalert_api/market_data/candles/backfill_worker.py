"""Long-running orchestration for asynchronous historical candle coverage.

The archive/checkpoint primitives from #151 and the coverage planner/state from
#153 provide the ``backfill_runtime`` coordinator consumed here. This module
owns only process lifecycle, the single active unit boundary, pacing, bounded
retry/backoff, shutdown, and safe operational logging. It never downloads,
parses, or writes candle data itself.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import logging
import signal
import time
from collections.abc import AsyncContextManager, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol, cast

from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.e2e.worker_gate import wait_for_worker_gate


logger = logging.getLogger(__name__)

BACKFILL_COORDINATOR_MODULE = (
    "freecoinalert_api.market_data.candles.backfill_runtime"
)
BACKFILL_COORDINATOR_FACTORY = "build_backfill_coordinator"
BACKFILL_LOCK_RETRY_SECONDS = 30
BACKFILL_FAILURE_BACKOFF_SECONDS = (5, 30, 120)

BackfillCoverageState = Literal["backfilling", "ready", "degraded"]
BackfillUnitState = Literal["committed", "deferred", "complete"]
CANDLE_BACKFILL_BEFORE_RUN_GATE = "candle_backfill_before_run"


@dataclass(frozen=True)
class BackfillCoverageStatus:
    """Safe coverage values returned by the #153 coverage boundary."""

    status: BackfillCoverageState
    available_start: datetime | None
    available_end: datetime | None
    target_start: datetime | None
    target_end: datetime | None
    coverage_percent: Decimal | None
    last_success_at: datetime | None
    last_error_category: str | None


@dataclass(frozen=True)
class BackfillWorkUnit:
    """One archive/checkpoint unit selected by the #151/#153 coordinator."""

    symbol: str
    archive_key: str
    period_start: datetime
    period_end: datetime
    archive_granularity: Literal["monthly", "daily"]


@dataclass(frozen=True)
class BackfillUnitResult:
    """The bounded result of one coordinator-owned import unit."""

    state: BackfillUnitState
    source_rows_written: int
    source_rows_unchanged: int
    source_rows_corrected: int
    derived_rows_written: int
    next_open_time: datetime | None
    failure_category: str | None = None


class BackfillLease(Protocol):
    """Dedicated #151 advisory-lock lease held only around one planning unit."""

    async def __aenter__(self) -> None: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


class BackfillCoordinator(Protocol):
    """Integration contract implemented by the #151/#153 data boundaries."""

    async def get_coverage_status(self) -> BackfillCoverageStatus: ...

    async def try_acquire_owner(self) -> AsyncContextManager[None] | None: ...

    async def next_work_unit(self) -> BackfillWorkUnit | None: ...

    async def process_work_unit(
        self,
        work_unit: BackfillWorkUnit,
        *,
        chunk_pause_seconds: float,
    ) -> BackfillUnitResult: ...

    async def defer_work_unit(
        self,
        work_unit: BackfillWorkUnit,
        *,
        failure_category: str,
    ) -> None: ...


BackfillCoordinatorFactory = Callable[[Settings], BackfillCoordinator]


class BackfillIntegrationUnavailable:
    """Degraded no-op when the canonical backfill adapter is unavailable."""

    async def get_coverage_status(self) -> BackfillCoverageStatus:
        return BackfillCoverageStatus(
            status="degraded",
            available_start=None,
            available_end=None,
            target_start=None,
            target_end=None,
            coverage_percent=None,
            last_success_at=None,
            last_error_category="backfill_integration_unavailable",
        )

    async def try_acquire_owner(self) -> None:
        return None

    async def next_work_unit(self) -> None:
        return None

    async def process_work_unit(
        self,
        work_unit: BackfillWorkUnit,
        *,
        chunk_pause_seconds: float,
    ) -> BackfillUnitResult:
        raise RuntimeError("The candle backfill coordinator is unavailable.")

    async def defer_work_unit(
        self,
        work_unit: BackfillWorkUnit,
        *,
        failure_category: str,
    ) -> None:
        return None


def build_backfill_coordinator(settings: Settings) -> BackfillCoordinator:
    """Load the coordinator adapter without making app readiness depend on it.

    A missing adapter keeps the background service alive and visibly degraded,
    while an adapter with an invalid contract fails loudly during worker startup.
    """

    try:
        module = importlib.import_module(BACKFILL_COORDINATOR_MODULE)
    except ModuleNotFoundError as error:
        if error.name != BACKFILL_COORDINATOR_MODULE:
            raise
        logger.warning(
            "market.candle.backfill.degraded category=backfill_integration_unavailable "
            "dependency=#151/#153"
        )
        return BackfillIntegrationUnavailable()

    factory = getattr(module, BACKFILL_COORDINATOR_FACTORY, None)
    if not callable(factory):
        raise RuntimeError(
            f"{BACKFILL_COORDINATOR_MODULE} must export "
            f"{BACKFILL_COORDINATOR_FACTORY}."
        )

    return cast(BackfillCoordinator, factory(settings))


class CandleBackfillWorker:
    """Keep historical coverage progressing without blocking application startup."""

    def __init__(
        self,
        *,
        settings: Settings,
        coordinator_factory: BackfillCoordinatorFactory = build_backfill_coordinator,
    ) -> None:
        self._settings = settings
        self._coordinator_factory = coordinator_factory
        self._stop_event = asyncio.Event()
        self._failure_attempt = 0
        self._last_status: tuple[object, ...] | None = None

    def request_shutdown(self) -> None:
        self._stop_event.set()

    async def run(self) -> int:
        self._install_signal_handlers()
        logger.info(
            "market.candle.backfill.starting target_days=%s maintenance_seconds=%s "
            "chunk_pause_seconds=%s",
            self._settings.candle_backfill_target_days,
            self._settings.candle_backfill_maintenance_seconds,
            self._settings.candle_backfill_chunk_pause_seconds,
        )
        coordinator = self._coordinator_factory(self._settings)

        while not self._stop_event.is_set():
            await wait_for_worker_gate(
                self._settings,
                gate_name=CANDLE_BACKFILL_BEFORE_RUN_GATE,
                stop_event=self._stop_event,
                default_blocked=self._settings.e2e_candle_backfill_paused,
            )
            if self._stop_event.is_set():
                break
            coverage = await coordinator.get_coverage_status()
            self._log_coverage_status(coverage)

            lease = await coordinator.try_acquire_owner()
            if lease is None:
                logger.info(
                    "market.candle.backfill.waiting category=backfill_owner_unavailable "
                    "retry_seconds=%s",
                    BACKFILL_LOCK_RETRY_SECONDS,
                )
                await self._sleep_or_stop(BACKFILL_LOCK_RETRY_SECONDS)
                continue

            work_unit: BackfillWorkUnit | None = None
            result: BackfillUnitResult | None = None
            deferred = False
            started_at = time.monotonic()
            async with lease:
                work_unit = await coordinator.next_work_unit()
                if work_unit is not None:
                    try:
                        result = await coordinator.process_work_unit(
                            work_unit,
                            chunk_pause_seconds=(
                                self._settings.candle_backfill_chunk_pause_seconds
                            ),
                        )
                    except SQLAlchemyError:
                        logger.exception(
                            "market.candle.backfill.failed "
                            "category=backfill_database_unavailable symbol=%s archive_key=%s",
                            work_unit.symbol,
                            work_unit.archive_key,
                        )
                        raise
                    except Exception:
                        self._failure_attempt += 1
                        category = "backfill_unit_failed"
                        logger.exception(
                            "market.candle.backfill.failed category=%s symbol=%s "
                            "archive_key=%s attempt=%s",
                            category,
                            work_unit.symbol,
                            work_unit.archive_key,
                            self._failure_attempt,
                        )
                        await coordinator.defer_work_unit(
                            work_unit,
                            failure_category=category,
                        )
                        deferred = True

            if work_unit is None:
                self._failure_attempt = 0
                await self._sleep_or_stop(
                    self._settings.candle_backfill_maintenance_seconds
                )
                continue
            if deferred:
                await self._sleep_or_stop(self._failure_backoff_seconds())
                continue
            if result is None:
                raise RuntimeError("The backfill coordinator returned no unit result.")

            self._failure_attempt = 0
            self._log_unit_result(
                work_unit,
                result,
                duration_seconds=time.monotonic() - started_at,
            )
            await self._sleep_or_stop(
                self._settings.candle_backfill_chunk_pause_seconds
            )

        logger.info("market.candle.backfill.stopped")
        return 0

    async def _sleep_or_stop(self, seconds: float) -> None:
        if seconds <= 0 or self._stop_event.is_set():
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except TimeoutError:
            return

    def _failure_backoff_seconds(self) -> int:
        index = min(
            max(self._failure_attempt - 1, 0),
            len(BACKFILL_FAILURE_BACKOFF_SECONDS) - 1,
        )
        return BACKFILL_FAILURE_BACKOFF_SECONDS[index]

    def _log_coverage_status(self, coverage: BackfillCoverageStatus) -> None:
        signature = (
            coverage.status,
            coverage.available_start,
            coverage.available_end,
            coverage.target_start,
            coverage.target_end,
            coverage.coverage_percent,
            coverage.last_success_at,
            coverage.last_error_category,
        )
        if signature == self._last_status:
            return
        self._last_status = signature
        logger.info(
            "market.candle.coverage_status status=%s available_start=%s "
            "available_end=%s target_start=%s target_end=%s coverage_percent=%s "
            "last_success_at=%s last_error_category=%s",
            coverage.status,
            coverage.available_start,
            coverage.available_end,
            coverage.target_start,
            coverage.target_end,
            coverage.coverage_percent,
            coverage.last_success_at,
            coverage.last_error_category,
        )

    @staticmethod
    def _log_unit_result(
        work_unit: BackfillWorkUnit,
        result: BackfillUnitResult,
        *,
        duration_seconds: float,
    ) -> None:
        event = (
            "completed"
            if result.state in {"complete", "committed"}
            else "deferred"
        )
        logger.info(
            "market.candle.archive.%s symbol=%s granularity=%s archive_key=%s "
            "source_rows_written=%s source_rows_unchanged=%s source_rows_corrected=%s "
            "derived_rows_written=%s next_open_time=%s failure_category=%s duration_seconds=%.3f",
            event,
            work_unit.symbol,
            work_unit.archive_granularity,
            work_unit.archive_key,
            result.source_rows_written,
            result.source_rows_unchanged,
            result.source_rows_corrected,
            result.derived_rows_written,
            result.next_open_time,
            result.failure_category,
            duration_seconds,
        )

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for signal_name in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(signal_name, self.request_shutdown)


async def run_backfill_worker() -> int:
    return await CandleBackfillWorker(settings=get_settings()).run()


def main() -> None:
    raise SystemExit(asyncio.run(run_backfill_worker()))


if __name__ == "__main__":
    main()
