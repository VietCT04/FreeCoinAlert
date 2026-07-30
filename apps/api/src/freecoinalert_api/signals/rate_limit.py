import asyncio
import time
from collections import deque

from freecoinalert_api.signals.errors import SignalError


class SignalRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str, *, limit: int) -> None:
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.setdefault(key, deque())
            while bucket and now - bucket[0] >= 900:
                bucket.popleft()
            if len(bucket) >= limit:
                raise SignalError(status_code=429, code="SIGNAL_SUBSCRIPTION_RATE_LIMITED", message="Too many subscription requests. Try again later.", retry_after=max(1, int(900 - (now - bucket[0])) + 1))
            bucket.append(now)
            while len(self._buckets) > 4096:
                self._buckets.pop(next(iter(self._buckets)))


signal_rate_limiter = SignalRateLimiter()


def enable_user_key(user_id: str) -> str:
    return f"signal-enable-user:{user_id}"


def enable_ip_key(client_ip: str) -> str:
    return f"signal-enable-ip:{client_ip}"


def disable_user_key(user_id: str) -> str:
    return f"signal-disable-user:{user_id}"
