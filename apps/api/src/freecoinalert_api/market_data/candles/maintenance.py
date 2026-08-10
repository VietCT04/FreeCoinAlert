from datetime import UTC, datetime, timedelta

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.repositories.market_candles import delete_candle_revisions_before
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.candles.constants import validate_candle_retention_days
from freecoinalert_api.market_data.candles.coverage import refresh_coverage_after_retention


async def cleanup_retention() -> int:
    retention_days = validate_candle_retention_days(get_settings().candle_retention_days)
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=retention_days)
    async with get_async_session_factory()() as session:
        async with session.begin():
            deleted = await delete_candle_revisions_before(session, cutoff=cutoff)
            await refresh_coverage_after_retention(session, now=now)
            return deleted
