import uuid
from datetime import datetime

from sqlalchemy import case, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.historical_analysis_run import HistoricalAnalysisRun
from freecoinalert_api.db.models.historical_analysis_report import HistoricalAnalysisReport


async def delete_expired_historical_analysis_runs(
    session: AsyncSession,
    *,
    expires_before: datetime,
    batch_size: int,
) -> int:
    terminal_at = case(
        (HistoricalAnalysisRun.status == "succeeded", HistoricalAnalysisRun.completed_at),
        (HistoricalAnalysisRun.status == "failed", HistoricalAnalysisRun.failed_at),
        (HistoricalAnalysisRun.status == "cancelled", HistoricalAnalysisRun.cancelled_at),
    )
    candidates = (
        await session.scalars(
            select(HistoricalAnalysisRun.id)
            .where(
                HistoricalAnalysisRun.status.in_(
                    ("succeeded", "failed", "cancelled"),
                ),
                terminal_at < expires_before,
            )
            .order_by(terminal_at.asc(), HistoricalAnalysisRun.id.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
    ).all()
    run_ids = [uuid.UUID(str(run_id)) for run_id in candidates]
    if not run_ids:
        return 0
    await session.execute(
        delete(HistoricalAnalysisReport).where(HistoricalAnalysisReport.run_id.in_(run_ids))
    )
    result = await session.execute(
        delete(HistoricalAnalysisRun).where(HistoricalAnalysisRun.id.in_(run_ids))
    )
    return int(result.rowcount or 0)
