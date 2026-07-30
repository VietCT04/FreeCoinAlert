import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class BinanceMetadataError(Exception):
    category: str
    retry_after_seconds: int | None = None


class BinancePublicMarketDataClient:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def get_spot_exchange_info(self, *, symbols: Sequence[str]) -> dict[str, object]:
        parameters = {"symbols": json.dumps(list(symbols), separators=(",", ":"))}

        async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
            return await self._request_exchange_info(client, parameters=parameters, retry_allowed=True)

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
