import asyncio
import time
from collections import deque

from freecoinalert_api.signals.errors import SignalError


class SignalRateLimiter:
    def __init__(
        self,
        *,
        error_code: str = "SIGNAL_SUBSCRIPTION_RATE_LIMITED",
        error_message: str = "Too many subscription requests. Try again later.",
    ) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._error_code = error_code
        self._error_message = error_message

    async def consume(self, key: str, *, limit: int) -> None:
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.setdefault(key, deque())
            while bucket and now - bucket[0] >= 900:
                bucket.popleft()
            if len(bucket) >= limit:
                raise SignalError(
                    status_code=429,
                    code=self._error_code,
                    message=self._error_message,
                    retry_after=max(1, int(900 - (now - bucket[0])) + 1),
                )
            bucket.append(now)
            while len(self._buckets) > 4096:
                self._buckets.pop(next(iter(self._buckets)))


signal_rate_limiter = SignalRateLimiter()
signal_feed_rate_limiter = SignalRateLimiter(
    error_code="SIGNAL_FEED_RATE_LIMITED",
    error_message="Too many signal feed requests. Try again later.",
)
signal_telegram_delivery_rate_limiter = SignalRateLimiter(
    error_code="SIGNAL_TELEGRAM_DELIVERY_RATE_LIMITED",
    error_message="Too many Telegram delivery preference requests. Try again later.",
)


def enable_user_key(user_id: str) -> str:
    return f"signal-enable-user:{user_id}"


def enable_ip_key(client_ip: str) -> str:
    return f"signal-enable-ip:{client_ip}"


def disable_user_key(user_id: str) -> str:
    return f"signal-disable-user:{user_id}"


def telegram_delivery_user_key(user_id: str) -> str:
    return f"signal-telegram-delivery-user:{user_id}"


def feed_history_user_key(user_id: str) -> str:
    return f"signal-feed-history-user:{user_id}"


def feed_stream_user_key(user_id: str) -> str:
    return f"signal-feed-stream-user:{user_id}"


def feed_stream_ip_key(client_ip: str) -> str:
    return f"signal-feed-stream-ip:{client_ip}"
