from datetime import UTC, datetime, timedelta

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.repositories.market_candles import delete_candle_revisions_before
from freecoinalert_api.db.session import get_async_session_factory


async def cleanup_retention() -> int:
    cutoff = datetime.now(UTC) - timedelta(days=get_settings().candle_retention_days)
    async with get_async_session_factory()() as session:
        async with session.begin():
            return await delete_candle_revisions_before(session, cutoff=cutoff)
