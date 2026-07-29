import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

from freecoinalert_api.api.errors import AuthenticationError

WINDOW_SECONDS = 15 * 60
MAXIMUM_BUCKETS = 4096


@dataclass
class AttemptBucket:
    timestamps: deque[float] = field(default_factory=deque)


class AuthenticationRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, AttemptBucket] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str, limit: int) -> None:
        async with self._lock:
            now = time.monotonic()
            self._remove_expired_buckets(now)
            bucket = self._buckets.setdefault(key, AttemptBucket())

            if len(bucket.timestamps) >= limit:
                retry_after = max(
                    1,
                    int(WINDOW_SECONDS - (now - bucket.timestamps[0])) + 1,
                )
                raise AuthenticationError(
                    status_code=429,
                    code="AUTH_RATE_LIMITED",
                    message="Too many authentication attempts. Try again later.",
                    retry_after=retry_after,
                )

            bucket.timestamps.append(now)
            self._bound_bucket_count()

    async def clear(self, key: str) -> None:
        async with self._lock:
            self._buckets.pop(key, None)

    def _remove_expired_buckets(self, now: float) -> None:
        expired_keys: list[str] = []

        for key, bucket in self._buckets.items():
            while bucket.timestamps and now - bucket.timestamps[0] >= WINDOW_SECONDS:
                bucket.timestamps.popleft()

            if not bucket.timestamps:
                expired_keys.append(key)

        for key in expired_keys:
            del self._buckets[key]

    def _bound_bucket_count(self) -> None:
        while len(self._buckets) > MAXIMUM_BUCKETS:
            key_to_remove = min(
                self._buckets,
                key=lambda key: self._buckets[key].timestamps[0],
            )
            del self._buckets[key_to_remove]


authentication_rate_limiter = AuthenticationRateLimiter()


def registration_ip_key(client_ip: str) -> str:
    return f"registration:{client_ip}"


def login_ip_key(client_ip: str) -> str:
    return f"login:{client_ip}"


def login_failure_key(client_ip: str, email_normalized: str) -> str:
    return f"login-failure:{client_ip}:{email_normalized}"
