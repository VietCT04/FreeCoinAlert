import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from uuid import UUID

from freecoinalert_api.signals.errors import SignalError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResetSignal:
    reason: str = "history_required"


QueueItem = int | ResetSignal


@dataclass(slots=True)
class SignalFeedConnection:
    user_id: UUID
    queue: asyncio.Queue[QueueItem]
    connection_id: UUID = field(default_factory=uuid.uuid4)
    replaying: bool = True
    replay_high_water_sequence: int = 0
    reset_requested: bool = False
    last_delivered_sequence: int = 0
    queued_sequences: set[int] = field(default_factory=set)

    def enqueue(self, sequence: int) -> None:
        if self.reset_requested or sequence <= self.last_delivered_sequence:
            return
        if sequence in self.queued_sequences:
            return
        try:
            self.queue.put_nowait(sequence)
        except asyncio.QueueFull:
            logger.warning(
                "signal.feed.backpressure user_id=%s connection_id=%s sequence=%s queue_size=%s",
                self.user_id,
                self.connection_id,
                sequence,
                self.queue.maxsize,
            )
            self.request_reset()
            return
        self.queued_sequences.add(sequence)

    def request_reset(self) -> None:
        if self.reset_requested:
            return
        self.reset_requested = True
        self._clear_queue()
        self.queue.put_nowait(ResetSignal())

    def finish_replay(self, high_water_sequence: int) -> None:
        self.replay_high_water_sequence = high_water_sequence
        self.replaying = False
        retained: list[QueueItem] = []
        while True:
            try:
                item = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            self.queue.task_done()
            if isinstance(item, ResetSignal) or item > high_water_sequence:
                retained.append(item)
            else:
                self.queued_sequences.discard(item)
        for item in retained:
            self.queue.put_nowait(item)

    def mark_delivered(self, sequence: int) -> None:
        self.queued_sequences.discard(sequence)
        self.last_delivered_sequence = max(self.last_delivered_sequence, sequence)

    def _clear_queue(self) -> None:
        while True:
            try:
                item = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            self.queue.task_done()
            if isinstance(item, int):
                self.queued_sequences.discard(item)


class SignalFeedConnectionManager:
    def __init__(
        self,
        *,
        max_connections_per_user: int,
        max_connections_per_process: int,
        queue_size: int,
    ) -> None:
        self.max_connections_per_user = max_connections_per_user
        self.max_connections_per_process = max_connections_per_process
        self.queue_size = queue_size
        self._connections: dict[UUID, dict[UUID, SignalFeedConnection]] = {}
        self._lock = asyncio.Lock()

    async def open(self, *, user_id: UUID) -> SignalFeedConnection:
        async with self._lock:
            user_connections = self._connections.get(user_id)
            if user_connections is None:
                user_connections = {}
            total_connections = sum(
                len(connections) for connections in self._connections.values()
            )
            if len(user_connections) >= self.max_connections_per_user:
                logger.info(
                    "signal.feed.connection_rejected user_id=%s category=user_limit",
                    user_id,
                )
                raise connection_limit_error()
            if total_connections >= self.max_connections_per_process:
                logger.info(
                    "signal.feed.connection_rejected user_id=%s category=process_limit",
                    user_id,
                )
                raise connection_limit_error()
            connection = SignalFeedConnection(
                user_id=user_id,
                queue=asyncio.Queue(maxsize=self.queue_size),
            )
            self._connections.setdefault(user_id, user_connections)
            user_connections[connection.connection_id] = connection
            logger.info(
                "signal.feed.connection_opened user_id=%s connection_id=%s active_connections=%s",
                user_id,
                connection.connection_id,
                total_connections + 1,
            )
            return connection

    async def close(self, connection: SignalFeedConnection, *, category: str) -> None:
        async with self._lock:
            user_connections = self._connections.get(connection.user_id)
            if user_connections is not None:
                user_connections.pop(connection.connection_id, None)
                if not user_connections:
                    self._connections.pop(connection.user_id, None)
            logger.info(
                "signal.feed.connection_closed user_id=%s connection_id=%s category=%s",
                connection.user_id,
                connection.connection_id,
                category,
            )

    async def publish(self, *, sequence: int, user_ids: list[UUID]) -> None:
        async with self._lock:
            for user_id in user_ids:
                for connection in self._connections.get(user_id, {}).values():
                    connection.enqueue(sequence)

    async def reset_all(self, *, category: str) -> None:
        async with self._lock:
            connections = [
                connection
                for user_connections in self._connections.values()
                for connection in user_connections.values()
            ]
            for connection in connections:
                connection.request_reset()
        logger.warning(
            "signal.feed.reset_required category=%s connection_count=%s",
            category,
            len(connections),
        )


def connection_limit_error() -> SignalError:
    return SignalError(
        status_code=429,
        code="SIGNAL_FEED_CONNECTION_LIMIT_REACHED",
        message="The signal feed connection limit has been reached.",
        retry_after=60,
    )
