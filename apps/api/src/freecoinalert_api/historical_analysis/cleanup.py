"""Explicit bounded cleanup command for terminal historical-analysis runs."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.repositories.historical_analysis_cleanup import (
    delete_expired_historical_analysis_runs,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.catalog import utc_now


logger = logging.getLogger(__name__)


async def cleanup_historical_analysis(settings: Settings) -> int:
    expires_before = utc_now() - timedelta(days=settings.historical_analysis_retention_days)
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        async with session.begin():
            deleted_count = await delete_expired_historical_analysis_runs(
                session,
                expires_before=expires_before,
                batch_size=settings.historical_analysis_cleanup_batch_size,
            )
    logger.info(
        "historical.analysis.cleanup_completed deleted_count=%s",
        deleted_count,
    )
    return deleted_count


def main() -> None:
    try:
        asyncio.run(cleanup_historical_analysis(get_settings()))
    except SQLAlchemyError:
        logger.info(
            "historical.analysis.failed failure_category=historical_analysis_persistence_failure"
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
