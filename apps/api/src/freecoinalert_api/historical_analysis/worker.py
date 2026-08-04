"""Restart-safe historical-analysis worker with immutable report publication."""

from __future__ import annotations

import asyncio
import logging
import signal
import uuid
from dataclasses import asdict
from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.models.historical_analysis_dataset import (
    HistoricalAnalysisDataset,
)
from freecoinalert_api.db.models.historical_analysis_dataset_candle import (
    HistoricalAnalysisDatasetCandle,
)
from freecoinalert_api.db.models.historical_analysis_run import HistoricalAnalysisRun
from freecoinalert_api.db.repositories.historical_analysis_datasets import (
    get_historical_analysis_dataset,
    list_historical_analysis_dataset_candles,
)
from freecoinalert_api.db.repositories.historical_analysis_reports import (
    create_historical_analysis_equity_points,
    create_historical_analysis_report,
    create_historical_analysis_trades,
    get_historical_analysis_report_by_run_id,
)
from freecoinalert_api.db.repositories.historical_analysis_runs import (
    get_historical_analysis_run_by_id,
)
from freecoinalert_api.db.repositories.historical_analysis_worker import (
    cancel_claimed_historical_analysis_run,
    claim_available_historical_analysis_runs,
    get_claimed_historical_analysis_run,
    mark_historical_analysis_progress,
    mark_historical_analysis_succeeded,
    recover_stale_historical_analysis_runs,
    requeue_or_fail_historical_analysis_run,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.e2e.worker_gate import (
    HISTORICAL_ANALYSIS_AFTER_CLAIM_GATE,
    HISTORICAL_ANALYSIS_BEFORE_CLAIM_GATE,
    HISTORICAL_ANALYSIS_BEFORE_RUN_GATE,
    wait_for_historical_worker_gate,
)
from freecoinalert_api.historical_analysis.datasets import (
    HistoricalAnalysisDatasetPreparationResult,
    HistoricalAnalysisDatasetValidationResult,
    prepare_historical_analysis_dataset,
    validate_historical_analysis_dataset_current,
    validate_historical_analysis_dataset_current_for_publication,
)
from freecoinalert_api.historical_analysis.engine import (
    HistoricalDatasetManifest,
    HistoricalPresetSnapshot,
    HistoricalSimulationCandle,
    HistoricalSimulationInput,
    HistoricalSimulationResult,
    simulate_fixed_preset,
)
from freecoinalert_api.market_data.catalog import utc_now


logger = logging.getLogger(__name__)

TERMINAL_DATASET_FAILURES = {
    "historical_dataset_insufficient_warmup",
    "historical_dataset_gap_detected",
    "historical_dataset_incomplete",
    "historical_dataset_invalid",
    "historical_dataset_too_large",
    "historical_dataset_stale",
}


class HistoricalAnalysisWorker:
    def __init__(
        self,
        *,
        settings: Settings,
        worker_id: str,
    ) -> None:
        self._settings = settings
        self._worker_id = worker_id
        self._stop_event = asyncio.Event()

    def request_shutdown(self) -> None:
        self._stop_event.set()

    async def run(self) -> None:
        await self._recover_stale_runs()
        while not self._stop_event.is_set():
            await wait_for_historical_worker_gate(
                self._settings,
                gate_name=HISTORICAL_ANALYSIS_BEFORE_CLAIM_GATE,
                stop_event=self._stop_event,
            )
            if self._stop_event.is_set():
                break
            claimed_runs = await self._claim_runs()
            if not claimed_runs:
                await self._sleep_until_work_or_shutdown()
                continue

            for run in claimed_runs:
                if self._stop_event.is_set():
                    break
                try:
                    await self._process_run(run.id)
                except SQLAlchemyError:
                    await self._handle_failure(
                        run.id,
                        failure_code="historical_analysis_persistence_failure",
                        retryable=True,
                    )
                except Exception:
                    await self._handle_failure(
                        run.id,
                        failure_code="historical_analysis_engine_failure",
                        retryable=False,
                    )

    async def _recover_stale_runs(self) -> None:
        current_time = utc_now()
        session_factory = get_async_session_factory()
        try:
            async with session_factory() as session:
                async with session.begin():
                    recovery = await recover_stale_historical_analysis_runs(
                        session,
                        stale_before=current_time
                        - timedelta(
                            seconds=self._settings.historical_analysis_worker_stale_seconds,
                        ),
                        current_time=current_time,
                    )
            for run in recovery.recovered:
                logger.info(
                    "historical.analysis.requeued run_id=%s attempt_count=%s "
                    "failure_category=historical_analysis_worker_recovered",
                    run.id,
                    run.attempt_count,
                )
            for run in recovery.exhausted:
                logger.info(
                    "historical.analysis.failed run_id=%s attempt_count=%s "
                    "failure_category=historical_analysis_attempts_exhausted",
                    run.id,
                    run.attempt_count,
                )
            for run in recovery.cancelled:
                logger.info(
                    "historical.analysis.cancelled run_id=%s attempt_count=%s",
                    run.id,
                    run.attempt_count,
                )
        except SQLAlchemyError:
            logger.info(
                "historical.analysis.failed failure_category=historical_analysis_persistence_failure"
            )

    async def _claim_runs(self) -> list[HistoricalAnalysisRun]:
        current_time = utc_now()
        session_factory = get_async_session_factory()
        try:
            async with session_factory() as session:
                async with session.begin():
                    runs = list(
                        await claim_available_historical_analysis_runs(
                            session,
                            current_time=current_time,
                            worker_id=self._worker_id,
                            limit=self._settings.historical_analysis_worker_claim_limit,
                        )
                    )
            for run in runs:
                logger.info(
                    "historical.analysis.claimed run_id=%s "
                    "engine_version=%s assumption_version=%s attempt_count=%s",
                    run.id,
                    run.simulation_version,
                    run.assumption_version,
                    run.attempt_count,
                )
            return runs
        except SQLAlchemyError:
            logger.info(
                "historical.analysis.failed failure_category=historical_analysis_persistence_failure"
            )
            return []

    async def _process_run(self, run_id: uuid.UUID) -> None:
        await wait_for_historical_worker_gate(
            self._settings,
            gate_name=HISTORICAL_ANALYSIS_AFTER_CLAIM_GATE,
            stop_event=self._stop_event,
        )
        await wait_for_historical_worker_gate(
            self._settings,
            gate_name=HISTORICAL_ANALYSIS_BEFORE_RUN_GATE,
            stop_event=self._stop_event,
        )
        if self._stop_event.is_set():
            return
        if not await self._ensure_running(run_id):
            return

        preparation = await self._prepare_dataset(run_id)
        if preparation.dataset is None or preparation.dataset.status != "ready":
            failure_code = _dataset_failure_code(preparation.failure_code)
            await self._handle_failure(
                run_id,
                failure_code=failure_code,
                retryable=preparation.failure_code == "historical_dataset_unavailable",
            )
            return
        if not await self._set_progress(run_id, stage="validating_dataset", percent=25):
            return

        validation = await self._validate_dataset(preparation.dataset.id)
        if validation.dataset is None or validation.failure_code is not None:
            failure_code = _dataset_failure_code(validation.failure_code)
            await self._handle_failure(
                run_id,
                failure_code=failure_code,
                retryable=validation.failure_code == "historical_dataset_unavailable",
            )
            return

        run, dataset, snapshots = await self._load_simulation_input(
            run_id,
            preparation.dataset.id,
        )
        if run is None or dataset is None or len(snapshots) > 2_500:
            await self._handle_failure(
                run_id,
                failure_code=(
                    "historical_dataset_too_large"
                    if len(snapshots) > 2_500
                    else "historical_analysis_unavailable"
                ),
                retryable=False,
            )
            return

        if not await self._set_progress(run_id, stage="simulating", percent=40):
            return

        simulation_input = _simulation_input(run, dataset, snapshots)
        try:
            result = simulate_fixed_preset(simulation_input)
        except Exception:
            await self._handle_failure(
                run_id,
                failure_code="historical_analysis_engine_failure",
                retryable=False,
            )
            return
        if result.status != "success":
            await self._handle_failure(
                run_id,
                failure_code=_simulation_failure_code(result),
                retryable=False,
            )
            return

        if not await self._ensure_running(run_id):
            return
        await self._publish_report(run_id, preparation.dataset.id, result)

    async def _prepare_dataset(
        self,
        run_id: uuid.UUID,
    ) -> HistoricalAnalysisDatasetPreparationResult:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            return await prepare_historical_analysis_dataset(session, run_id)

    async def _validate_dataset(
        self,
        dataset_id: uuid.UUID,
    ) -> HistoricalAnalysisDatasetValidationResult:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            return await validate_historical_analysis_dataset_current(session, dataset_id)

    async def _load_simulation_input(
        self,
        run_id: uuid.UUID,
        dataset_id: uuid.UUID,
    ) -> tuple[
        HistoricalAnalysisRun | None,
        HistoricalAnalysisDataset | None,
        list[HistoricalAnalysisDatasetCandle],
    ]:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            run = await get_historical_analysis_run_by_id(session, run_id=run_id)
            dataset = await get_historical_analysis_dataset(session, dataset_id=dataset_id)
            snapshots = list(
                await list_historical_analysis_dataset_candles(
                    session,
                    dataset_id=dataset_id,
                )
            )
            return run, dataset, snapshots

    async def _publish_report(
        self,
        run_id: uuid.UUID,
        dataset_id: uuid.UUID,
        result: HistoricalSimulationResult,
    ) -> None:
        session_factory = get_async_session_factory()
        try:
            async with session_factory() as session:
                async with session.begin():
                    run = await get_claimed_historical_analysis_run(
                        session,
                        run_id=run_id,
                        worker_id=self._worker_id,
                    )
                    if run is None:
                        return
                    if run.cancellation_requested_at is not None:
                        await cancel_claimed_historical_analysis_run(
                            session,
                            run_id=run_id,
                            worker_id=self._worker_id,
                        )
                        logger.info(
                            "historical.analysis.cancelled run_id=%s",
                            run_id,
                        )
                        return
                    run.progress_stage = "persisting_report"
                    run.progress_percent = 90
                    run.updated_at = utc_now()

                    validation = await validate_historical_analysis_dataset_current_for_publication(
                        session,
                        dataset_id,
                    )
                    if validation.failure_code is not None:
                        await requeue_or_fail_historical_analysis_run(
                            session,
                            run_id=run_id,
                            worker_id=self._worker_id,
                            failure_code=_dataset_failure_code(validation.failure_code),
                            retryable=validation.failure_code == "historical_dataset_unavailable",
                        )
                        return
                    if validation.dataset is None or validation.dataset.status != "ready":
                        await requeue_or_fail_historical_analysis_run(
                            session,
                            run_id=run_id,
                            worker_id=self._worker_id,
                            failure_code="historical_dataset_stale",
                            retryable=False,
                        )
                        return
                    if validation.dataset.manifest_fingerprint != result.dataset_fingerprint:
                        validation.dataset.status = "stale"
                        validation.dataset.failure_code = "historical_dataset_stale"
                        validation.dataset.stale_at = utc_now()
                        await requeue_or_fail_historical_analysis_run(
                            session,
                            run_id=run_id,
                            worker_id=self._worker_id,
                            failure_code="historical_dataset_stale",
                            retryable=False,
                        )
                        return

                    existing = await get_historical_analysis_report_by_run_id(
                        session,
                        run_id=run_id,
                        for_update=True,
                    )
                    if existing is not None:
                        if existing.result_fingerprint != result.result_fingerprint:
                            await requeue_or_fail_historical_analysis_run(
                                session,
                                run_id=run_id,
                                worker_id=self._worker_id,
                                failure_code="historical_analysis_result_conflict",
                                retryable=False,
                            )
                            return
                        completed_at = utc_now()
                        if await mark_historical_analysis_succeeded(
                            session,
                            run=run,
                            worker_id=self._worker_id,
                            completed_at=completed_at,
                        ):
                            logger.info(
                                "historical.analysis.succeeded run_id=%s report_id=%s "
                                "dataset_id=%s trade_count=%s duration_seconds=%s",
                                run.id,
                                existing.id,
                                existing.dataset_id,
                                existing.trade_count,
                                (completed_at - run.created_at).total_seconds(),
                            )
                        return

                    report = await _create_report_rows(
                        session,
                        run=run,
                        result=result,
                        dataset=validation.dataset,
                    )
                    completed_at = utc_now()
                    if await mark_historical_analysis_succeeded(
                        session,
                        run=run,
                        worker_id=self._worker_id,
                        completed_at=completed_at,
                    ):
                        logger.info(
                            "historical.analysis.succeeded run_id=%s report_id=%s "
                            "dataset_id=%s trade_count=%s duration_seconds=%s",
                            run.id,
                            report.id,
                            report.dataset_id,
                            report.trade_count,
                            (completed_at - run.created_at).total_seconds(),
                        )
        except SQLAlchemyError:
            await self._handle_failure(
                run_id,
                failure_code="historical_analysis_persistence_failure",
                retryable=True,
            )

    async def _ensure_running(self, run_id: uuid.UUID) -> bool:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            async with session.begin():
                run = await get_claimed_historical_analysis_run(
                    session,
                    run_id=run_id,
                    worker_id=self._worker_id,
                )
                if run is None:
                    return False
                if run.cancellation_requested_at is None:
                    return True
                await cancel_claimed_historical_analysis_run(
                    session,
                    run_id=run_id,
                    worker_id=self._worker_id,
                )
        logger.info("historical.analysis.cancelled run_id=%s", run_id)
        return False

    async def _set_progress(self, run_id: uuid.UUID, *, stage: str, percent: int) -> bool:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            async with session.begin():
                updated = await mark_historical_analysis_progress(
                    session,
                    run_id=run_id,
                    worker_id=self._worker_id,
                    stage=stage,
                    percent=percent,
                )
        if updated:
            logger.info(
                "historical.analysis.progress run_id=%s stage=%s percent=%s",
                run_id,
                stage,
                percent,
            )
        else:
            logger.info("historical.analysis.cancelled run_id=%s", run_id)
        return updated

    async def _handle_failure(
        self,
        run_id: uuid.UUID,
        *,
        failure_code: str,
        retryable: bool,
    ) -> None:
        session_factory = get_async_session_factory()
        try:
            async with session_factory() as session:
                async with session.begin():
                    status = await requeue_or_fail_historical_analysis_run(
                        session,
                        run_id=run_id,
                        worker_id=self._worker_id,
                        failure_code=failure_code,
                        retryable=retryable,
                    )
            if status == "queued":
                logger.info(
                    "historical.analysis.requeued run_id=%s failure_category=%s",
                    run_id,
                    "historical_analysis_worker_retry",
                )
            elif status == "cancelled":
                logger.info("historical.analysis.cancelled run_id=%s", run_id)
            elif status == "failed":
                logger.info(
                    "historical.analysis.failed run_id=%s failure_category=%s",
                    run_id,
                    failure_code if not retryable else "historical_analysis_attempts_exhausted",
                )
        except SQLAlchemyError:
            logger.info(
                "historical.analysis.failed run_id=%s "
                "failure_category=historical_analysis_persistence_failure",
                run_id,
            )

    async def _sleep_until_work_or_shutdown(self) -> None:
        try:
            await asyncio.wait_for(
                self._stop_event.wait(),
                timeout=self._settings.historical_analysis_worker_poll_seconds,
            )
        except TimeoutError:
            return


async def _create_report_rows(
    session,
    *,
    run: HistoricalAnalysisRun,
    result: HistoricalSimulationResult,
    dataset: HistoricalAnalysisDataset,
):
    serialized = result.to_serializable()
    summary = result.summary
    if summary is None or result.result_fingerprint is None or result.dataset_fingerprint is None:
        raise ValueError("A successful simulation must contain a complete result.")
    assumptions_snapshot = dict(serialized["assumptions"] or {})
    assumptions_snapshot["schema_version"] = "historical_analysis_assumptions_snapshot_v1"
    assumptions_snapshot["safety_disclosures"] = list(result.safety_disclosures)
    report = await create_historical_analysis_report(
        session,
        run_id=run.id,
        user_id=run.user_id,
        dataset_id=dataset.id,
        result_fingerprint=result.result_fingerprint,
        dataset_fingerprint=result.dataset_fingerprint,
        engine_version=result.engine_version or run.simulation_version,
        assumption_version=result.assumption_version or run.assumption_version,
        calculation_version=result.calculation_version or run.calculation_version_snapshot,
        market_snapshot=_market_snapshot(run),
        preset_snapshot=_preset_snapshot(run),
        coverage_snapshot=_coverage_snapshot(dataset),
        assumptions_snapshot=assumptions_snapshot,
        analysis_start=run.analysis_start,
        analysis_end=run.analysis_end,
        analysis_candle_count=summary.analysis_candle_count,
        signal_count=summary.signal_count,
        trade_count=summary.executed_trade_count,
        winning_trade_count=summary.winning_trade_count,
        losing_trade_count=summary.losing_trade_count,
        flat_trade_count=summary.flat_trade_count,
        overlapping_signal_count=summary.overlapping_signal_count,
        insufficient_forward_signal_count=summary.insufficient_forward_window_signal_count,
        equity_exhausted_signal_count=summary.equity_exhausted_signal_count,
        initial_equity=summary.initial_equity,
        final_equity=summary.final_equity,
        gross_return=summary.gross_return,
        net_return=summary.net_return,
        maximum_drawdown=summary.maximum_drawdown,
        win_rate=summary.win_rate,
        win_rate_undefined_reason=summary.win_rate_undefined_reason,
        profit_factor=summary.profit_factor,
        profit_factor_undefined_reason=summary.profit_factor_undefined_reason,
    )
    await create_historical_analysis_trades(
        session,
        report_id=report.id,
        trades=tuple(asdict(trade) for trade in result.trades),
    )
    await create_historical_analysis_equity_points(
        session,
        report_id=report.id,
        points=tuple(
            {
                "sequence": point.sequence,
                "candle_id": point.candle_id,
                "candle_revision": point.candle_revision,
                "open_time": point.candle_open_time,
                "close_time": point.candle_close_time,
                "equity": point.equity,
                "drawdown": point.drawdown,
                "position_state": point.position_state,
                "active_trade_sequence": point.active_trade_sequence,
            }
            for point in result.equity_series
        ),
    )
    return report


def _simulation_input(
    run: HistoricalAnalysisRun,
    dataset: HistoricalAnalysisDataset,
    snapshots: list[HistoricalAnalysisDatasetCandle],
) -> HistoricalSimulationInput:
    manifest = HistoricalDatasetManifest(
        dataset_id=dataset.id,
        supported_market_id=dataset.supported_market_id,
        signal_preset_id=dataset.signal_preset_id,
        status=dataset.status,
        timeframe=dataset.timeframe,
        analysis_start=dataset.analysis_start,
        analysis_end=dataset.analysis_end,
        warmup_start=dataset.warmup_start,
        required_warmup_candles=dataset.required_warmup_candles,
        warmup_candle_count=dataset.warmup_candle_count,
        analysis_candle_count=dataset.analysis_candle_count,
        total_candle_count=dataset.total_candle_count,
        first_open_time=dataset.first_open_time,
        last_close_time=dataset.last_close_time,
        manifest_fingerprint=dataset.manifest_fingerprint,
    )
    preset = HistoricalPresetSnapshot(
        preset_id=run.signal_preset_id,
        code=run.preset_code_snapshot,
        version=run.preset_version_snapshot,
        strategy_type=run.strategy_type_snapshot,
        timeframe=run.timeframe_snapshot,
        direction=run.direction_snapshot,
        period=run.period_snapshot,
        threshold=run.threshold_snapshot,
        price_input=run.price_input_snapshot,
    )
    candles = tuple(
        HistoricalSimulationCandle(
            dataset_id=snapshot.dataset_id,
            position=snapshot.position,
            candle_id=snapshot.candle_id,
            candle_revision=snapshot.candle_revision,
            is_warmup=snapshot.is_warmup,
            timeframe=snapshot.timeframe,
            open_time=snapshot.open_time,
            close_time=snapshot.close_time,
            open_price=snapshot.open_price,
            high_price=snapshot.high_price,
            low_price=snapshot.low_price,
            close_price=snapshot.close_price,
            base_volume=snapshot.base_volume,
            quote_volume=snapshot.quote_volume,
            trade_count=snapshot.trade_count,
            source_kind=snapshot.source_kind,
            source_candle_count=snapshot.source_candle_count,
            expected_source_candle_count=snapshot.expected_source_candle_count,
            source_fingerprint=snapshot.source_fingerprint,
        )
        for snapshot in snapshots
    )
    return HistoricalSimulationInput(
        dataset=manifest,
        preset=preset,
        calculation_version=run.calculation_version_snapshot,
        analysis_start=run.analysis_start,
        analysis_end=run.analysis_end,
        candles=candles,
        engine_version=run.simulation_version,
        assumption_version=run.assumption_version,
    )


def _dataset_failure_code(failure_code: str | None) -> str:
    if failure_code == "historical_dataset_correction_race":
        return "historical_dataset_stale"
    if failure_code in TERMINAL_DATASET_FAILURES:
        return failure_code
    return "historical_analysis_unavailable"


def _simulation_failure_code(result: HistoricalSimulationResult) -> str:
    if result.status == "insufficient_history":
        return "historical_dataset_insufficient_warmup"
    if result.status == "gap_detected":
        return "historical_dataset_gap_detected"
    if result.status in {
        "unsupported_preset",
        "unsupported_calculation_version",
        "unsupported_engine_version",
        "unsupported_assumption_version",
    }:
        return "historical_simulation_unsupported_version"
    if result.status == "invalid_input":
        return "historical_simulation_invalid_input"
    return "historical_analysis_engine_failure"


def _market_snapshot(run: HistoricalAnalysisRun) -> dict[str, object]:
    return {
        "schema_version": "historical_analysis_market_snapshot_v1",
        "exchange": run.exchange_snapshot,
        "market_type": run.market_type_snapshot,
        "symbol": run.symbol_snapshot,
        "base_asset": run.base_asset_snapshot,
        "quote_asset": run.quote_asset_snapshot,
    }


def _preset_snapshot(run: HistoricalAnalysisRun) -> dict[str, object]:
    return {
        "schema_version": "historical_analysis_preset_snapshot_v1",
        "code": run.preset_code_snapshot,
        "version": run.preset_version_snapshot,
        "name": run.preset_name_snapshot,
        "strategy_type": run.strategy_type_snapshot,
        "timeframe": run.timeframe_snapshot,
        "direction": run.direction_snapshot,
        "period": run.period_snapshot,
        "threshold": (
            None if run.threshold_snapshot is None else format(run.threshold_snapshot, "f")
        ),
        "price_input": run.price_input_snapshot,
    }


def _coverage_snapshot(dataset: HistoricalAnalysisDataset) -> dict[str, object]:
    return {
        "schema_version": "historical_analysis_coverage_snapshot_v1",
        "timeframe": dataset.timeframe,
        "analysis_start": dataset.analysis_start.isoformat(),
        "analysis_end": dataset.analysis_end.isoformat(),
        "warmup_start": dataset.warmup_start.isoformat(),
        "required_warmup_candles": dataset.required_warmup_candles,
        "warmup_candle_count": dataset.warmup_candle_count,
        "analysis_candle_count": dataset.analysis_candle_count,
        "total_candle_count": dataset.total_candle_count,
        "first_open_time": dataset.first_open_time.isoformat(),
        "last_close_time": dataset.last_close_time.isoformat(),
        "manifest_fingerprint": dataset.manifest_fingerprint,
    }


def create_worker() -> HistoricalAnalysisWorker:
    return HistoricalAnalysisWorker(
        settings=get_settings(),
        worker_id=str(uuid.uuid4()),
    )


def main() -> None:
    worker = create_worker()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, worker.request_shutdown)
        except NotImplementedError:
            signal.signal(signal_name, lambda *_: worker.request_shutdown())
    try:
        loop.run_until_complete(worker.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
