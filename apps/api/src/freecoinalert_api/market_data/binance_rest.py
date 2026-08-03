import asyncio
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

import httpx


@dataclass(frozen=True)
class BinanceMetadataError(Exception):
    category: str
    retry_after_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class BinanceKline:
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    base_volume: Decimal
    quote_volume: Decimal
    trade_count: int
    first_trade_id: int | None
    last_trade_id: int | None


class BinancePublicMarketDataClient:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def get_spot_exchange_info(self, *, symbols: Sequence[str]) -> dict[str, object]:
        parameters = {"symbols": json.dumps(list(symbols), separators=(",", ":"))}

        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            return await self._request_exchange_info(client, parameters=parameters, retry_allowed=True)

    async def get_spot_klines(
        self,
        *,
        symbol: str,
        start_open_time: datetime,
        end_open_time: datetime,
    ) -> list[BinanceKline]:
        if start_open_time.tzinfo is None or end_open_time.tzinfo is None:
            raise BinanceMetadataError("invalid_kline_range")
        parameters = {
            "symbol": symbol,
            "interval": "1m",
            "startTime": str(int(start_open_time.astimezone(UTC).timestamp() * 1000)),
            "endTime": str(int((end_open_time.astimezone(UTC) - timedelta(milliseconds=1)).timestamp() * 1000)),
            "limit": "1000",
        }
        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            for attempt in range(3):
                try:
                    response = await client.get("/api/v3/klines", params=parameters)
                except httpx.RequestError as error:
                    if attempt == 2:
                        raise BinanceMetadataError("network") from error
                    await asyncio.sleep((2**attempt) * (1 + random.uniform(0, 0.25)))
                    continue
                if response.status_code == 418:
                    raise BinanceMetadataError("binance_ip_banned")
                if response.status_code == 429:
                    if attempt:
                        raise BinanceMetadataError("rate_limited")
                    delay = parse_retry_after(response.headers.get("Retry-After"))
                    if delay is None:
                        raise BinanceMetadataError("rate_limited")
                    await asyncio.sleep(delay)
                    continue
                if response.status_code >= 500:
                    if attempt == 2:
                        raise BinanceMetadataError("provider_server_error")
                    await asyncio.sleep((2**attempt) * (1 + random.uniform(0, 0.25)))
                    continue
                if response.status_code >= 400:
                    raise BinanceMetadataError("provider_response_invalid")
                return parse_klines(response.json(), start_open_time=start_open_time, end_open_time=end_open_time)
        raise BinanceMetadataError("kline_retry_exhausted")

    async def _request_exchange_info(
        self,
        client: httpx.AsyncClient,
        *,
        parameters: dict[str, str],
        retry_allowed: bool,
    ) -> dict[str, object]:
        try:
            response = await client.get("/api/v3/exchangeInfo", params=parameters)
        except httpx.TimeoutException as error:
            raise BinanceMetadataError("timeout") from error
        except httpx.RequestError as error:
            raise BinanceMetadataError("network") from error

        if response.status_code in {418, 429}:
            retry_after_seconds = parse_retry_after(response.headers.get("Retry-After"))

            if retry_allowed and retry_after_seconds is not None:
                await asyncio.sleep(min(retry_after_seconds, 60))
                return await self._request_exchange_info(
                    client,
                    parameters=parameters,
                    retry_allowed=False,
                )

            raise BinanceMetadataError("rate_limited", retry_after_seconds)

        if response.status_code >= 500:
            raise BinanceMetadataError("provider_server_error")

        if response.status_code >= 400:
            raise BinanceMetadataError("provider_response_invalid")

        try:
            payload = response.json()
        except json.JSONDecodeError as error:
            raise BinanceMetadataError("malformed_json") from error

        if not isinstance(payload, dict):
            raise BinanceMetadataError("malformed_response")

        return payload


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
        close_time = kline_timestamp(row[6]) + timedelta(milliseconds=1)
        if open_time < start_open_time or open_time >= end_open_time or close_time != open_time + timedelta(minutes=1):
            raise BinanceMetadataError("invalid_kline_bounds")
        if previous is not None and open_time != previous + timedelta(minutes=1):
            raise BinanceMetadataError("nonconsecutive_kline_response")
        kline = BinanceKline(
            open_time=open_time, close_time=close_time,
            open_price=kline_decimal(row[1]), high_price=kline_decimal(row[2]),
            low_price=kline_decimal(row[3]), close_price=kline_decimal(row[4]),
            base_volume=kline_decimal(row[5]), quote_volume=kline_decimal(row[7]),
            trade_count=kline_int(row[8]), first_trade_id=None, last_trade_id=None,
        )
        if kline.high_price < max(kline.open_price, kline.close_price) or kline.low_price > min(kline.open_price, kline.close_price):
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
