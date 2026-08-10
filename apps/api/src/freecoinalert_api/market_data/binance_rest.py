import asyncio
import json
import logging
import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Callable

import httpx

from freecoinalert_api.db.repositories.provider_rest_rate_state import (
    lock_provider_rest_rate_state,
)
from freecoinalert_api.db.session import get_async_session_factory

logger = logging.getLogger(__name__)

BINANCE_SPOT_REST_PROVIDER_KEY = "binance_spot_rest"
EXCHANGE_INFO_REQUEST_WEIGHT = 20
KLINES_REQUEST_WEIGHT = 2
BOOTSTRAP_REQUEST_WEIGHT_LIMIT = 1200
SAFE_REQUEST_WEIGHT_RATIO = 0.8
MAX_TRANSIENT_ATTEMPTS = 3
DEFAULT_429_BLOCK_SECONDS = 60
DEFAULT_418_BLOCK_SECONDS = 60 * 60
MAX_KLINE_PAGE_MINUTES = 1000
_WEIGHT_HEADER_PATTERN = re.compile(r"^x-mbx-used-weight-(\d+)([smhd])$")


@dataclass(frozen=True)
class BinanceMetadataError(Exception):
    category: str
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.category)


@dataclass(frozen=True, slots=True)
class BinanceKline:
    open_time: datetime
    close_time: datetime
    provider_close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    base_volume: Decimal
    quote_volume: Decimal
    trade_count: int
    first_trade_id: int | None
    last_trade_id: int | None


def _utc_now() -> datetime:
    return datetime.now(UTC)


class BinanceRestRateBudget:
    """Coordinate Binance Spot REST request weight through PostgreSQL state.

    The object contains no local quota state. Every process uses the same
    ``provider_rest_rate_state`` row, so separate catalogue, bootstrap, and
    stream processes reserve against one conservative provider-IP budget.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = _utc_now,
        random_source: Callable[[], float] | None = None,
    ) -> None:
        self._clock = clock
        self._random_source = random_source or random.random

    def now(self) -> datetime:
        return self._clock().astimezone(UTC)

    async def reserve(self, *, route: str, weight: int) -> None:
        if weight <= 0:
            raise ValueError("Binance REST request weight must be positive.")

        while True:
            now = self._clock().astimezone(UTC)
            wait_seconds: float | None = None
            async with get_async_session_factory()() as session:
                async with session.begin():
                    state = await lock_provider_rest_rate_state(
                        session,
                        provider_key=BINANCE_SPOT_REST_PROVIDER_KEY,
                        now=now,
                    )
                    if state.blocked_until is not None and state.blocked_until > now:
                        raise self._blocked_error(
                            state.blocked_reason,
                            retry_after_seconds=max(
                                1,
                                int((state.blocked_until - now).total_seconds() + 0.999999),
                            ),
                        )
                    if state.blocked_until is not None:
                        state.blocked_until = None
                        state.blocked_reason = None

                    provider_limit = state.provider_limit_weight or BOOTSTRAP_REQUEST_WEIGHT_LIMIT
                    safe_limit = max(1, int(provider_limit * SAFE_REQUEST_WEIGHT_RATIO))
                    effective_used = max(state.reserved_weight, state.provider_used_weight)
                    if effective_used + weight > safe_limit:
                        next_window = state.window_started_at.astimezone(UTC) + timedelta(minutes=1)
                        wait_seconds = max(0.01, (next_window - now).total_seconds())
                    else:
                        state.reserved_weight = effective_used + weight

            if wait_seconds is None:
                return

            jitter = 0.01 + self._random_source() * 0.24
            total_wait = wait_seconds + jitter
            logger.info(
                "binance.rest.local_throttled route=%s weight=%s wait_ms=%s",
                route,
                weight,
                int(total_wait * 1000),
            )
            await asyncio.sleep(total_wait)

    async def observe_response(
        self,
        *,
        headers: Mapping[str, str],
        response_at: datetime | None = None,
    ) -> None:
        observed_weights: dict[str, int] = {}
        for header_name, raw_value in headers.items():
            normalized_name = header_name.lower()
            match = _WEIGHT_HEADER_PATTERN.fullmatch(normalized_name)
            if match is None:
                if normalized_name.startswith("x-mbx-used-weight-"):
                    logger.warning(
                        "binance.rest.weight_header_invalid header=%s value=%s",
                        header_name,
                        raw_value,
                    )
                continue
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                logger.warning(
                    "binance.rest.weight_header_invalid header=%s value=%s",
                    header_name,
                    raw_value,
                )
                continue
            if value < 0:
                logger.warning(
                    "binance.rest.weight_header_invalid header=%s value=%s",
                    header_name,
                    raw_value,
                )
                continue
            observed_weights[match.group(2)] = max(observed_weights.get(match.group(2), 0), value)

        now = (response_at or self.now()).astimezone(UTC)
        async with get_async_session_factory()() as session:
            async with session.begin():
                state = await lock_provider_rest_rate_state(
                    session,
                    provider_key=BINANCE_SPOT_REST_PROVIDER_KEY,
                    now=now,
                )
                observed_one_minute = observed_weights.get("m")
                if observed_one_minute is not None:
                    state.provider_used_weight = max(
                        state.provider_used_weight,
                        observed_one_minute,
                    )
                state.last_response_at = now

        if observed_weights:
            provider_limit = await self.provider_limit()
            logger.info(
                "binance.rest.weight_observed used=%s limit=%s safe_limit=%s",
                observed_weights.get("m"),
                provider_limit,
                max(1, int(provider_limit * SAFE_REQUEST_WEIGHT_RATIO)),
            )

    async def block(
        self,
        *,
        reason: str,
        retry_after_seconds: int | None,
        response_at: datetime | None = None,
    ) -> int:
        if reason not in {"rate_limited", "ip_banned"}:
            raise ValueError("Unsupported Binance REST block reason.")
        default_seconds = (
            DEFAULT_418_BLOCK_SECONDS if reason == "ip_banned" else DEFAULT_429_BLOCK_SECONDS
        )
        delay = retry_after_seconds or default_seconds
        now = (response_at or self.now()).astimezone(UTC)
        requested_until = now + timedelta(seconds=delay)
        async with get_async_session_factory()() as session:
            async with session.begin():
                state = await lock_provider_rest_rate_state(
                    session,
                    provider_key=BINANCE_SPOT_REST_PROVIDER_KEY,
                    now=now,
                )
                existing_until = state.blocked_until
                if existing_until is None or requested_until > existing_until:
                    state.blocked_until = requested_until
                    state.blocked_reason = reason
                elif reason == "ip_banned" or state.blocked_reason == "ip_banned":
                    state.blocked_reason = "ip_banned"
                    reason = "ip_banned"
                effective_until = state.blocked_until or requested_until
                effective_delay = max(
                    1,
                    int((effective_until - now).total_seconds() + 0.999999),
                )

        event_name = "ip_banned" if reason == "ip_banned" else "rate_limited"
        logger.error(
            "binance.rest.%s retry_after_seconds=%s",
            event_name,
            effective_delay,
        )
        return effective_delay

    async def learn_provider_limit(self, payload: object) -> None:
        limit = parse_request_weight_limit(payload)
        if limit is None:
            return
        now = self.now()
        async with get_async_session_factory()() as session:
            async with session.begin():
                state = await lock_provider_rest_rate_state(
                    session,
                    provider_key=BINANCE_SPOT_REST_PROVIDER_KEY,
                    now=now,
                )
                state.provider_limit_weight = limit

    async def provider_limit(self) -> int:
        now = self.now()
        async with get_async_session_factory()() as session:
            async with session.begin():
                state = await lock_provider_rest_rate_state(
                    session,
                    provider_key=BINANCE_SPOT_REST_PROVIDER_KEY,
                    now=now,
                )
                return state.provider_limit_weight or BOOTSTRAP_REQUEST_WEIGHT_LIMIT

    def _blocked_error(self, reason: str | None, retry_after_seconds: int) -> BinanceMetadataError:
        if reason == "ip_banned":
            return BinanceMetadataError("binance_ip_banned", retry_after_seconds)
        return BinanceMetadataError("rate_limited", retry_after_seconds)


shared_binance_rest_rate_budget = BinanceRestRateBudget()


class BinancePublicMarketDataClient:
    def __init__(
        self,
        *,
        base_url: str,
        rate_budget: BinanceRestRateBudget | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._rate_budget = rate_budget or shared_binance_rest_rate_budget

    async def get_spot_exchange_info(self, *, symbols: Sequence[str]) -> dict[str, object]:
        parameters = {"symbols": json.dumps(list(symbols), separators=(",", ":"))}
        payload = await self._request_json(
            route="exchangeInfo",
            weight=EXCHANGE_INFO_REQUEST_WEIGHT,
            parameters=parameters,
        )
        if not isinstance(payload, dict):
            raise BinanceMetadataError("malformed_response")
        await self._rate_budget.learn_provider_limit(payload)
        return payload

    async def get_spot_klines(
        self,
        *,
        symbol: str,
        start_open_time: datetime,
        end_open_time: datetime,
    ) -> list[BinanceKline]:
        if start_open_time.tzinfo is None or end_open_time.tzinfo is None:
            raise BinanceMetadataError("invalid_kline_range")
        start_open_time = start_open_time.astimezone(UTC)
        end_open_time = end_open_time.astimezone(UTC)
        if (
            start_open_time >= end_open_time
            or end_open_time - start_open_time > timedelta(minutes=MAX_KLINE_PAGE_MINUTES)
        ):
            raise BinanceMetadataError("invalid_kline_range")
        parameters = {
            "symbol": symbol,
            "interval": "1m",
            "startTime": str(int(start_open_time.timestamp() * 1000)),
            "endTime": str(int((end_open_time - timedelta(milliseconds=1)).timestamp() * 1000)),
            "limit": "1000",
        }
        payload = await self._request_json(
            route="klines",
            weight=KLINES_REQUEST_WEIGHT,
            parameters=parameters,
        )
        return parse_klines(
            payload,
            start_open_time=start_open_time,
            end_open_time=end_open_time,
        )

    async def _request_json(
        self,
        *,
        route: str,
        weight: int,
        parameters: dict[str, str],
    ) -> object:
        path = f"/api/v3/{route}"
        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            for attempt in range(MAX_TRANSIENT_ATTEMPTS):
                await self._rate_budget.reserve(route=route, weight=weight)
                logger.info(
                    "binance.rest.request_started route=%s weight=%s attempt=%s",
                    route,
                    weight,
                    attempt + 1,
                )
                try:
                    response = await client.get(path, params=parameters)
                except httpx.TimeoutException as error:
                    if attempt == MAX_TRANSIENT_ATTEMPTS - 1:
                        raise BinanceMetadataError("timeout") from error
                    await self._retry(category="timeout", attempt=attempt)
                    continue
                except httpx.RequestError as error:
                    if attempt == MAX_TRANSIENT_ATTEMPTS - 1:
                        raise BinanceMetadataError("network") from error
                    await self._retry(category="network", attempt=attempt)
                    continue

                response_at = self._rate_budget.now()
                await self._rate_budget.observe_response(
                    headers=response.headers,
                    response_at=response_at,
                )
                if response.status_code == 429:
                    retry_after = await self._rate_budget.block(
                        reason="rate_limited",
                        retry_after_seconds=parse_retry_after(response.headers.get("Retry-After")),
                        response_at=response_at,
                    )
                    raise BinanceMetadataError("rate_limited", retry_after)
                if response.status_code == 418:
                    retry_after = await self._rate_budget.block(
                        reason="ip_banned",
                        retry_after_seconds=parse_retry_after(response.headers.get("Retry-After")),
                        response_at=response_at,
                    )
                    raise BinanceMetadataError("binance_ip_banned", retry_after)
                if response.status_code >= 500:
                    if attempt == MAX_TRANSIENT_ATTEMPTS - 1:
                        raise BinanceMetadataError("provider_server_error")
                    await self._retry(category="provider_server_error", attempt=attempt)
                    continue
                if response.status_code >= 400:
                    raise BinanceMetadataError("provider_response_invalid")
                try:
                    return response.json()
                except ValueError as error:
                    raise BinanceMetadataError("malformed_json") from error

        raise BinanceMetadataError("provider_request_exhausted")

    async def _retry(self, *, category: str, attempt: int) -> None:
        delay = (2**attempt) * (1 + random.uniform(0, 0.25))
        logger.warning(
            "binance.rest.retry category=%s attempt=%s delay_seconds=%s",
            category,
            attempt + 1,
            delay,
        )
        await asyncio.sleep(delay)


def parse_request_weight_limit(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    raw_limits = payload.get("rateLimits")
    if not isinstance(raw_limits, list):
        return None
    for raw_limit in raw_limits:
        if not isinstance(raw_limit, dict):
            continue
        if (
            raw_limit.get("rateLimitType") != "REQUEST_WEIGHT"
            or raw_limit.get("interval") != "MINUTE"
            or raw_limit.get("intervalNum") != 1
        ):
            continue
        value = raw_limit.get("limit")
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            logger.warning("binance.rest.weight_limit_invalid category=exchange_info")
            return None
        return value
    return None


def parse_retry_after(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        seconds = int(value)
    except ValueError:
        return None

    return seconds if seconds > 0 else None


def parse_klines(
    payload: object,
    *,
    start_open_time: datetime,
    end_open_time: datetime,
) -> list[BinanceKline]:
    if not isinstance(payload, list):
        raise BinanceMetadataError("malformed_kline_response")
    result: list[BinanceKline] = []
    previous: datetime | None = None
    for row in payload:
        if not isinstance(row, list) or len(row) < 12:
            raise BinanceMetadataError("malformed_kline_response")
        open_time = kline_timestamp(row[0])
        provider_close_time = kline_timestamp(row[6])
        close_time = provider_close_time + timedelta(milliseconds=1)
        if (
            open_time < start_open_time
            or open_time >= end_open_time
            or close_time != open_time + timedelta(minutes=1)
        ):
            raise BinanceMetadataError("invalid_kline_bounds")
        if previous is not None and open_time != previous + timedelta(minutes=1):
            raise BinanceMetadataError("nonconsecutive_kline_response")
        kline = BinanceKline(
            open_time=open_time,
            close_time=close_time,
            provider_close_time=provider_close_time,
            open_price=kline_decimal(row[1]),
            high_price=kline_decimal(row[2]),
            low_price=kline_decimal(row[3]),
            close_price=kline_decimal(row[4]),
            base_volume=kline_decimal(row[5]),
            quote_volume=kline_decimal(row[7]),
            trade_count=kline_int(row[8]),
            first_trade_id=None,
            last_trade_id=None,
        )
        if (
            any(
                price <= 0
                for price in (
                    kline.open_price,
                    kline.high_price,
                    kline.low_price,
                    kline.close_price,
                )
            )
            or kline.high_price < max(kline.open_price, kline.close_price)
            or kline.low_price > min(kline.open_price, kline.close_price)
        ):
            raise BinanceMetadataError("impossible_kline_ohlc")
        result.append(kline)
        previous = open_time
    return result


def kline_timestamp(value: object) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BinanceMetadataError("malformed_kline_timestamp")
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def kline_decimal(value: object) -> Decimal:
    if not isinstance(value, str):
        raise BinanceMetadataError("malformed_kline_decimal")
    try:
        decimal_value = Decimal(value)
    except InvalidOperation as error:
        raise BinanceMetadataError("malformed_kline_decimal") from error
    if not decimal_value.is_finite() or decimal_value < 0:
        raise BinanceMetadataError("malformed_kline_decimal")
    return decimal_value


def kline_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BinanceMetadataError("malformed_kline_integer")
    return value
