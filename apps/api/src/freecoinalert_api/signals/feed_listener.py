import asyncio
import json
import logging
import random
from datetime import UTC, datetime, timedelta

from psycopg import AsyncConnection
from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.repositories.signal_feed_stream_events import (
    SIGNAL_FEED_CHANNEL,
    delete_old_stream_events,
    get_stream_record,
)
from freecoinalert_api.db.repositories.signal_subscriptions import list_active_subscriber_user_ids
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.signals.feed_connections import SignalFeedConnectionManager

logger = logging.getLogger(__name__)
RECONNECT_MAX_SECONDS = 30
STREAM_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60


class SignalFeedListener:
    def __init__(
        self,
        *,
        connection_manager: SignalFeedConnectionManager,
        settings: Settings | None = None,
    ) -> None:
        self.connection_manager = connection_manager
        self.settings = settings or get_settings()
        self._stop_event = asyncio.Event()
        self._listener_task: asyncio.Task[None] | None = None
        self._maintenance_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._listener_task is not None:
            return
        self._stop_event.clear()
        self._listener_task = asyncio.create_task(
            self._run_listener(),
            name="signal-feed-listener",
        )
        self._maintenance_task = asyncio.create_task(
            self._run_maintenance(),
            name="signal-feed-maintenance",
        )

    async def stop(self) -> None:
        self._stop_event.set()
        tasks = [task for task in (self._listener_task, self._maintenance_task) if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._listener_task = None
        self._maintenance_task = None

    async def _run_listener(self) -> None:
        reconnect_attempt = 0
        while not self._stop_event.is_set():
            try:
                await self._listen_once()
                reconnect_attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as error:
                category = type(error).__name__.lower()
                logger.warning("signal.feed.listener_failed category=%s", category)
                await self.connection_manager.reset_all(category="listener_unavailable")
                reconnect_attempt += 1
                delay = min(
                    2 ** max(reconnect_attempt - 1, 0),
                    RECONNECT_MAX_SECONDS,
                )
                delay += random.uniform(0, delay * 0.25)
                logger.info(
                    "signal.feed.listener_reconnecting attempt=%s delay_seconds=%s",
                    reconnect_attempt,
                    delay,
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
                except TimeoutError:
                    pass

    async def _listen_once(self) -> None:
        connection = await AsyncConnection.connect(
            psycopg_dsn(self.settings.database_url),
            autocommit=True,
        )
        try:
            await connection.execute(f"LISTEN {SIGNAL_FEED_CHANNEL}")
            logger.info("signal.feed.listener_connected channel=%s", SIGNAL_FEED_CHANNEL)
            async for notification in connection.notifies():
                if self._stop_event.is_set():
                    return
                sequence = parse_notification_sequence(notification.payload)
                if sequence is None:
                    logger.warning("signal.feed.listener_failed category=invalid_notification")
                    continue
                await self._dispatch_sequence(sequence)
        finally:
            await connection.close()

    async def _dispatch_sequence(self, sequence: int) -> None:
        async with get_async_session_factory()() as session:
            record = await get_stream_record(session, sequence=sequence)
            if record is None:
                logger.warning(
                    "signal.feed.listener_failed category=stream_row_missing sequence=%s",
                    sequence,
                )
                return
            user_ids = list(
                await list_active_subscriber_user_ids(
                    session,
                    supported_market_id=record.signal_event.supported_market_id,
                    signal_preset_id=record.signal_event.signal_preset_id,
                )
            )
        logger.info(
            "signal.feed.event_published sequence=%s kind=%s user_count=%s",
            sequence,
            record.stream_event.kind,
            len(user_ids),
        )
        await self.connection_manager.publish(sequence=sequence, user_ids=user_ids)

    async def _run_maintenance(self) -> None:
        while not self._stop_event.is_set():
            await self._cleanup_stream_rows()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=STREAM_CLEANUP_INTERVAL_SECONDS,
                )
            except TimeoutError:
                continue

    async def _cleanup_stream_rows(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(
            days=self.settings.signal_stream_retention_days,
        )
        try:
            async with get_async_session_factory()() as session:
                async with session.begin():
                    deleted = await delete_old_stream_events(session, cutoff=cutoff)
            if deleted:
                logger.info("signal.feed.stream_cleanup deleted_count=%s", deleted)
        except SQLAlchemyError:
            logger.warning("signal.feed.stream_cleanup_failed category=database_error")


def psycopg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
    return database_url


def parse_notification_sequence(payload: str) -> int | None:
    try:
        value = json.loads(payload)["sequence"]
        sequence = int(value)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if sequence < 1:
        return None
    return sequence
