import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import AuthenticationSettings
from freecoinalert_api.db.repositories.telegram import delete_processed_telegram_updates_before
from freecoinalert_api.db.session import get_async_session_factory

logger = logging.getLogger(__name__)

UPDATE_CLEANUP_LIMIT = 1_000


class TelegramUpdateCleanup:
    def __init__(self) -> None:
        self._last_attempt_at: datetime | None = None

    async def run_if_due(self, *, settings: AuthenticationSettings) -> None:
        now = datetime.now(timezone.utc)

        if self._last_attempt_at is not None and now - self._last_attempt_at < timedelta(days=1):
            return

        self._last_attempt_at = now
        cutoff = now - timedelta(days=settings.telegram_update_retention_days)
        session_factory = get_async_session_factory()

        try:
            async with session_factory() as session:
                await delete_processed_telegram_updates_before(
                    session,
                    cutoff=cutoff,
                    limit=UPDATE_CLEANUP_LIMIT,
                )
                await session.commit()
        except SQLAlchemyError:
            logger.error("telegram.update.cleanup_failed")


telegram_update_cleanup = TelegramUpdateCleanup()
