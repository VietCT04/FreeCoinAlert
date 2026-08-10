"""Historical-analysis coverage service boundary.

The implementation reads canonical database state only. Market-data coverage
planning and background acquisition are separate process responsibilities.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.repositories.historical_analysis_coverage import (
    HistoricalAnalysisCoverage,
    get_historical_analysis_coverage,
)


class HistoricalAnalysisCoverageService:
    async def resolve(
        self,
        session: AsyncSession,
        *,
        supported_market_id: uuid.UUID,
        timeframe: str,
        start_open_time: datetime,
        end_open_time: datetime,
        timeframe_delta: timedelta,
        expected_candle_count: int,
    ) -> HistoricalAnalysisCoverage:
        return await get_historical_analysis_coverage(
            session,
            supported_market_id=supported_market_id,
            timeframe=timeframe,
            start_open_time=start_open_time,
            end_open_time=end_open_time,
            timeframe_delta=timeframe_delta,
            expected_candle_count=expected_candle_count,
        )


historical_analysis_coverage_service = HistoricalAnalysisCoverageService()
