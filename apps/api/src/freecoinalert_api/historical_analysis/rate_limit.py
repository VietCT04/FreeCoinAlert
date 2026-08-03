import asyncio
import time
from collections import deque

from freecoinalert_api.historical_analysis.errors import HistoricalAnalysisError

WINDOW_SECONDS = 15 * 60
MAXIMUM_BUCKETS = 4096


class HistoricalAnalysisRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def consume(self, key: str, *, limit: int) -> None:
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.setdefault(key, deque())
            while bucket and now - bucket[0] >= WINDOW_SECONDS:
                bucket.popleft()

            if len(bucket) >= limit:
                raise HistoricalAnalysisError(
                    status_code=429,
                    code="HISTORICAL_ANALYSIS_RATE_LIMITED",
                    message="Too many historical-analysis requests. Try again later.",
                    retry_after=max(1, int(WINDOW_SECONDS - (now - bucket[0])) + 1),
                )

            bucket.append(now)
            while len(self._buckets) > MAXIMUM_BUCKETS:
                self._buckets.pop(next(iter(self._buckets)))


historical_analysis_rate_limiter = HistoricalAnalysisRateLimiter()


def create_user_key(user_id: str) -> str:
    return f"historical-analysis-create-user:{user_id}"


def create_ip_key(client_ip: str) -> str:
    return f"historical-analysis-create-ip:{client_ip}"


def cancel_user_key(user_id: str) -> str:
    return f"historical-analysis-cancel-user:{user_id}"


def read_user_key(user_id: str) -> str:
    return f"historical-analysis-read-user:{user_id}"

