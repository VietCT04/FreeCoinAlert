import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.historical_analysis_run import HistoricalAnalysisRun
from freecoinalert_api.market_data.catalog import utc_now


RETRY_DELAYS = {
    1: timedelta(seconds=5),
    2: timedelta(seconds=30),
    3: timedelta(minutes=2),
}


@dataclass(frozen=True, slots=True)
class HistoricalAnalysisRecoveryResult:
    recovered: tuple[HistoricalAnalysisRun, ...]
    exhausted: tuple[HistoricalAnalysisRun, ...]
    cancelled: tuple[HistoricalAnalysisRun, ...]


async def claim_available_historical_analysis_runs(
    session: AsyncSession,
    *,
    current_time: datetime,
    worker_id: str,
    limit: int,
) -> Sequence[HistoricalAnalysisRun]:
    statement = (
        select(HistoricalAnalysisRun)
        .where(
            HistoricalAnalysisRun.status == "queued",
            HistoricalAnalysisRun.available_at <= current_time,
            HistoricalAnalysisRun.cancellation_requested_at.is_(None),
            HistoricalAnalysisRun.attempt_count < HistoricalAnalysisRun.max_attempts,
        )
        .order_by(
            HistoricalAnalysisRun.available_at.asc(),
            HistoricalAnalysisRun.created_at.asc(),
            HistoricalAnalysisRun.id.asc(),
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    runs = list((await session.scalars(statement)).all())
    for run in runs:
        run.status = "running"
        run.progress_stage = "preparing_dataset"
        run.progress_percent = 10
        run.locked_at = current_time
        run.locked_by = worker_id
        run.started_at = run.started_at or current_time
        run.attempt_count += 1
        run.updated_at = current_time
    return runs


async def recover_stale_historical_analysis_runs(
    session: AsyncSession,
    *,
    stale_before: datetime,
    current_time: datetime,
) -> HistoricalAnalysisRecoveryResult:
    statement = (
        select(HistoricalAnalysisRun)
        .where(
            HistoricalAnalysisRun.status == "running",
            HistoricalAnalysisRun.locked_at.is_not(None),
            HistoricalAnalysisRun.locked_at < stale_before,
        )
        .order_by(HistoricalAnalysisRun.locked_at.asc(), HistoricalAnalysisRun.id.asc())
        .with_for_update(skip_locked=True)
    )
    runs = (await session.scalars(statement)).all()
    recovered: list[HistoricalAnalysisRun] = []
    exhausted: list[HistoricalAnalysisRun] = []
    cancelled: list[HistoricalAnalysisRun] = []

    for run in runs:
        if run.cancellation_requested_at is not None:
            _mark_cancelled(run, current_time)
            cancelled.append(run)
        elif run.attempt_count >= run.max_attempts:
            _mark_failed(run, current_time, "historical_analysis_attempts_exhausted")
            exhausted.append(run)
        else:
            _requeue(run, current_time)
            recovered.append(run)

    return HistoricalAnalysisRecoveryResult(
        recovered=tuple(recovered),
        exhausted=tuple(exhausted),
        cancelled=tuple(cancelled),
    )


async def mark_historical_analysis_progress(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    worker_id: str,
    stage: str,
    percent: int,
) -> bool:
    run = await _get_claimed_run(session, run_id=run_id, worker_id=worker_id)
    if run is None:
        return False
    if run.cancellation_requested_at is not None:
        _mark_cancelled(run, utc_now())
        return False
    run.progress_stage = stage
    run.progress_percent = percent
    run.updated_at = utc_now()
    return True


async def requeue_or_fail_historical_analysis_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    worker_id: str,
    failure_code: str,
    retryable: bool,
) -> str | None:
    run = await _get_claimed_run(session, run_id=run_id, worker_id=worker_id)
    if run is None:
        return None
    current_time = utc_now()
    if run.cancellation_requested_at is not None:
        _mark_cancelled(run, current_time)
        return run.status
    if retryable and run.attempt_count < run.max_attempts:
        _requeue(run, current_time)
        return run.status
    _mark_failed(
        run,
        current_time,
        failure_code if not retryable else "historical_analysis_attempts_exhausted",
    )
    return run.status


async def cancel_claimed_historical_analysis_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    worker_id: str,
) -> bool:
    run = await _get_claimed_run(session, run_id=run_id, worker_id=worker_id)
    if run is None:
        return False
    _mark_cancelled(run, utc_now())
    return True


async def mark_historical_analysis_succeeded(
    session: AsyncSession,
    *,
    run: HistoricalAnalysisRun,
    worker_id: str,
    completed_at: datetime,
) -> bool:
    if (
        run.status != "running"
        or run.locked_by != worker_id
        or run.cancellation_requested_at is not None
    ):
        return False
    run.status = "succeeded"
    run.progress_stage = "completed"
    run.progress_percent = 100
    run.completed_at = completed_at
    run.failure_code = None
    run.locked_at = None
    run.locked_by = None
    run.updated_at = completed_at
    return True


async def get_claimed_historical_analysis_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    worker_id: str,
) -> HistoricalAnalysisRun | None:
    return await _get_claimed_run(session, run_id=run_id, worker_id=worker_id)


async def _get_claimed_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    worker_id: str,
) -> HistoricalAnalysisRun | None:
    statement = (
        select(HistoricalAnalysisRun)
        .where(
            HistoricalAnalysisRun.id == run_id,
            HistoricalAnalysisRun.status == "running",
            HistoricalAnalysisRun.locked_by == worker_id,
        )
        .with_for_update()
    )
    return await session.scalar(statement)


def _requeue(run: HistoricalAnalysisRun, current_time: datetime) -> None:
    run.status = "queued"
    run.progress_stage = "queued"
    run.progress_percent = 0
    run.available_at = current_time + RETRY_DELAYS.get(
        run.attempt_count,
        RETRY_DELAYS[max(RETRY_DELAYS)],
    )
    run.locked_at = None
    run.locked_by = None
    run.failure_code = None
    run.completed_at = None
    run.failed_at = None
    run.cancelled_at = None
    run.updated_at = current_time


def _mark_failed(
    run: HistoricalAnalysisRun,
    current_time: datetime,
    failure_code: str,
) -> None:
    run.status = "failed"
    run.progress_stage = "failed"
    run.progress_percent = 100
    run.failed_at = current_time
    run.failure_code = failure_code
    run.locked_at = None
    run.locked_by = None
    run.completed_at = None
    run.cancelled_at = None
    run.updated_at = current_time


def _mark_cancelled(run: HistoricalAnalysisRun, current_time: datetime) -> None:
    run.status = "cancelled"
    run.progress_stage = "cancelled"
    run.cancelled_at = current_time
    run.cancellation_requested_at = run.cancellation_requested_at or current_time
    run.failure_code = None
    run.locked_at = None
    run.locked_by = None
    run.completed_at = None
    run.failed_at = None
    run.updated_at = current_time
