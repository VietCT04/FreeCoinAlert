"""Binance public-data archive planning, download, and full-file validation."""

import asyncio
import csv
import hashlib
import io
import re
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from typing import BinaryIO, Literal
from uuid import UUID
from zipfile import BadZipFile, ZipFile

import httpx

from freecoinalert_api.market_data.events import CanonicalOneMinuteCandleInput


ArchiveGranularity = Literal["monthly", "daily"]
ARCHIVE_INTERVAL = "1m"
ARCHIVE_TIMESTAMP_SWITCH = datetime(2025, 1, 1, tzinfo=UTC)
ARCHIVE_SPOOL_MAX_BYTES = 256 * 1024 * 1024
ARCHIVE_MAX_ATTEMPTS = 3
BINANCE_SPOT_KLINE_COLUMNS = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
)


class BinanceArchiveError(Exception):
    def __init__(self, category: str, message: str | None = None) -> None:
        super().__init__(message or category)
        self.category = category


@dataclass(frozen=True, slots=True)
class BinanceArchiveDescriptor:
    symbol: str
    granularity: ArchiveGranularity
    period_start: datetime
    period_end: datetime
    archive_key: str

    @property
    def archive_filename(self) -> str:
        return PurePosixPath(self.archive_key).name

    @property
    def csv_filename(self) -> str:
        return self.archive_filename.removesuffix(".zip") + ".csv"

    @property
    def checksum_key(self) -> str:
        return f"{self.archive_key}.CHECKSUM"


@dataclass(frozen=True, slots=True)
class BinanceArchiveCandidate:
    primary: BinanceArchiveDescriptor
    daily_fallbacks: tuple[BinanceArchiveDescriptor, ...]


@dataclass(slots=True)
class DownloadedBinanceArchive:
    descriptor: BinanceArchiveDescriptor
    checksum_sha256: str
    file: BinaryIO
    received_at: datetime

    def close(self) -> None:
        self.file.close()


def build_archive_descriptor(
    *,
    symbol: str,
    granularity: ArchiveGranularity,
    period_start: datetime,
) -> BinanceArchiveDescriptor:
    period_start = _normalize_minute(period_start)
    if granularity == "monthly":
        if period_start.day != 1 or period_start.hour or period_start.minute:
            raise ValueError("Monthly archive periods must start at the first UTC day.")
        period_end = _next_month(period_start)
        period_label = period_start.strftime("%Y-%m")
    else:
        if period_start.hour or period_start.minute:
            raise ValueError("Daily archive periods must start at UTC midnight.")
        period_end = period_start + timedelta(days=1)
        period_label = period_start.strftime("%Y-%m-%d")
    filename = f"{symbol}-{ARCHIVE_INTERVAL}-{period_label}.zip"
    archive_key = f"data/spot/{granularity}/klines/{symbol}/{ARCHIVE_INTERVAL}/{filename}"
    return BinanceArchiveDescriptor(
        symbol=symbol,
        granularity=granularity,
        period_start=period_start,
        period_end=period_end,
        archive_key=archive_key,
    )


def plan_archive_candidates(
    *,
    symbol: str,
    start_open_time: datetime,
    end_open_time: datetime,
    now: datetime,
) -> tuple[BinanceArchiveCandidate, ...]:
    """Plan immutable archive periods without owning coverage state or REST fallback."""

    start_open_time = _normalize_minute(start_open_time)
    end_open_time = _normalize_minute(end_open_time)
    now = _normalize_minute(now)
    if start_open_time >= end_open_time:
        raise ValueError("Archive planning requires a non-empty UTC range.")

    candidates: list[BinanceArchiveCandidate] = []
    month_start = start_open_time.replace(day=1, hour=0, minute=0)
    while month_start < end_open_time:
        month_end = _next_month(month_start)
        daily_periods = _completed_daily_descriptors(
            symbol=symbol,
            start_open_time=max(start_open_time, month_start),
            end_open_time=min(end_open_time, month_end),
            now=now,
        )
        if month_end <= now:
            candidates.append(
                BinanceArchiveCandidate(
                    primary=build_archive_descriptor(
                        symbol=symbol,
                        granularity="monthly",
                        period_start=month_start,
                    ),
                    daily_fallbacks=tuple(daily_periods),
                )
            )
        else:
            candidates.extend(
                BinanceArchiveCandidate(primary=daily, daily_fallbacks=())
                for daily in daily_periods
            )
        month_start = month_end
    return tuple(candidates)


class BinancePublicDataArchiveClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 30.0,
        max_attempts: int = ARCHIVE_MAX_ATTEMPTS,
    ) -> None:
        if max_attempts < 1 or max_attempts > ARCHIVE_MAX_ATTEMPTS:
            raise ValueError("Archive retries exceed the bounded policy.")
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 10.0))
        self._max_attempts = max_attempts

    async def download(
        self,
        descriptor: BinanceArchiveDescriptor,
    ) -> DownloadedBinanceArchive:
        async with httpx.AsyncClient(
            base_url=self._base_url,
            follow_redirects=True,
            timeout=self._timeout,
        ) as client:
            checksum_body = await self._get_text(client, descriptor.checksum_key)
            checksum = parse_checksum_text(
                checksum_body,
                expected_filename=descriptor.archive_filename,
            )
            archive_file = tempfile.SpooledTemporaryFile(
                max_size=ARCHIVE_SPOOL_MAX_BYTES,
                mode="w+b",
            )
            try:
                digest = await self._stream_archive(
                    client,
                    path=f"/{descriptor.archive_key}",
                    destination=archive_file,
                )
                if digest != checksum:
                    raise BinanceArchiveError("checksum_mismatch")
                archive_file.seek(0)
                return DownloadedBinanceArchive(
                    descriptor=descriptor,
                    checksum_sha256=checksum,
                    file=archive_file,
                    received_at=datetime.now(UTC),
                )
            except Exception:
                archive_file.close()
                raise

    async def _stream_archive(
        self,
        client: httpx.AsyncClient,
        *,
        path: str,
        destination: BinaryIO,
    ) -> str:
        for attempt in range(self._max_attempts):
            try:
                async with client.stream("GET", path) as response:
                    if response.status_code == 404:
                        raise BinanceArchiveError("archive_not_available")
                    if response.status_code >= 500:
                        if attempt + 1 == self._max_attempts:
                            raise BinanceArchiveError("provider_server_error")
                        await asyncio.sleep(2**attempt)
                        continue
                    if response.status_code >= 400:
                        raise BinanceArchiveError("provider_response_invalid")
                    destination.seek(0)
                    destination.truncate(0)
                    digest = hashlib.sha256()
                    total_bytes = 0
                    async for block in response.aiter_bytes():
                        total_bytes += len(block)
                        if total_bytes > ARCHIVE_SPOOL_MAX_BYTES:
                            raise BinanceArchiveError("archive_too_large")
                        digest.update(block)
                        destination.write(block)
                    return digest.hexdigest()
            except httpx.RequestError as error:
                if attempt + 1 == self._max_attempts:
                    raise BinanceArchiveError("network") from error
                await asyncio.sleep(2**attempt)
        raise BinanceArchiveError("archive_request_exhausted")

    async def _get_text(self, client: httpx.AsyncClient, path: str) -> str:
        response = await self._get_response(client, f"/{path.lstrip('/')}")
        return response.text

    async def _get_response(self, client: httpx.AsyncClient, path: str) -> httpx.Response:
        for attempt in range(self._max_attempts):
            try:
                response = await client.get(path)
            except httpx.RequestError as error:
                if attempt + 1 == self._max_attempts:
                    raise BinanceArchiveError("network") from error
                await asyncio.sleep(2**attempt)
                continue
            if response.status_code == 404:
                raise BinanceArchiveError("archive_not_available")
            if response.status_code >= 500:
                if attempt + 1 == self._max_attempts:
                    raise BinanceArchiveError("provider_server_error")
                await asyncio.sleep(2**attempt)
                continue
            if response.status_code >= 400:
                raise BinanceArchiveError("provider_response_invalid")
            return response
        raise BinanceArchiveError("archive_request_exhausted")


def parse_checksum_text(checksum_text: str, *, expected_filename: str) -> str:
    lines = [line.strip() for line in checksum_text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise BinanceArchiveError("checksum_format_invalid")
    match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?([^\s]+)", lines[0])
    if match is None or match.group(2) != expected_filename:
        raise BinanceArchiveError("checksum_format_invalid")
    return match.group(1).lower()


def parse_and_validate_archive(
    downloaded: DownloadedBinanceArchive,
    *,
    supported_market_id: UUID,
) -> list[CanonicalOneMinuteCandleInput]:
    descriptor = downloaded.descriptor
    timestamp_unit = _timestamp_unit(descriptor.period_start)
    try:
        with ZipFile(downloaded.file) as archive:
            members = [member for member in archive.namelist() if member == descriptor.csv_filename]
            if len(members) != 1:
                raise BinanceArchiveError("archive_member_invalid")
            with archive.open(members[0], "r") as member:
                text_stream = io.TextIOWrapper(member, encoding="utf-8", newline="")
                try:
                    rows = _parse_rows(
                        text_stream,
                        descriptor=descriptor,
                        supported_market_id=supported_market_id,
                        timestamp_unit=timestamp_unit,
                        received_at=downloaded.received_at,
                    )
                finally:
                    text_stream.detach()
    except (BadZipFile, UnicodeDecodeError, csv.Error) as error:
        raise BinanceArchiveError("archive_corrupt") from error

    expected_count = int((descriptor.period_end - descriptor.period_start) / timedelta(minutes=1))
    if len(rows) != expected_count:
        raise BinanceArchiveError("archive_incomplete")
    if not rows or rows[0].open_time != descriptor.period_start:
        raise BinanceArchiveError("archive_period_invalid")
    if rows[-1].close_time != descriptor.period_end:
        raise BinanceArchiveError("archive_period_invalid")
    return rows


def _parse_rows(
    text_stream: io.TextIOBase,
    *,
    descriptor: BinanceArchiveDescriptor,
    supported_market_id: UUID,
    timestamp_unit: timedelta,
    received_at: datetime,
) -> list[CanonicalOneMinuteCandleInput]:
    rows: list[CanonicalOneMinuteCandleInput] = []
    previous_open_time: datetime | None = None
    reader = csv.reader(text_stream)
    for row_index, raw_row in enumerate(reader):
        if row_index == 0 and tuple(raw_row) == BINANCE_SPOT_KLINE_COLUMNS:
            continue
        if len(raw_row) != len(BINANCE_SPOT_KLINE_COLUMNS):
            raise BinanceArchiveError("archive_columns_invalid")
        open_time = _archive_timestamp(raw_row[0], timestamp_unit)
        provider_close_time = _archive_timestamp(raw_row[6], timestamp_unit)
        close_time = open_time + timedelta(minutes=1)
        if (
            open_time < descriptor.period_start
            or open_time >= descriptor.period_end
            or close_time != open_time + timedelta(minutes=1)
            or provider_close_time + timestamp_unit != close_time
        ):
            raise BinanceArchiveError("archive_timestamp_invalid")
        if previous_open_time is not None and open_time != previous_open_time + timedelta(minutes=1):
            raise BinanceArchiveError("archive_nonconsecutive")
        open_price = _archive_price(raw_row[1])
        high_price = _archive_price(raw_row[2])
        low_price = _archive_price(raw_row[3])
        close_price = _archive_price(raw_row[4])
        base_volume = _archive_nonnegative_decimal(raw_row[5])
        quote_volume = _archive_nonnegative_decimal(raw_row[7])
        trade_count = _archive_nonnegative_int(raw_row[8])
        _archive_nonnegative_decimal(raw_row[9])
        _archive_nonnegative_decimal(raw_row[10])
        if raw_row[11] == "":
            raise BinanceArchiveError("archive_columns_invalid")
        if high_price < max(open_price, close_price, low_price) or low_price > min(
            open_price, close_price
        ):
            raise BinanceArchiveError("archive_ohlc_invalid")
        rows.append(
            CanonicalOneMinuteCandleInput(
                exchange="binance",
                market_type="spot",
                supported_market_id=supported_market_id,
                symbol=descriptor.symbol,
                timeframe="1m",
                open_time=open_time,
                close_time=close_time,
                provider_close_time=provider_close_time,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                base_volume=base_volume,
                quote_volume=quote_volume,
                trade_count=trade_count,
                first_trade_id=None,
                last_trade_id=None,
                provider_event_time=None,
                received_at=received_at,
            )
        )
        previous_open_time = open_time
    return rows


def _completed_daily_descriptors(
    *,
    symbol: str,
    start_open_time: datetime,
    end_open_time: datetime,
    now: datetime,
) -> list[BinanceArchiveDescriptor]:
    descriptors: list[BinanceArchiveDescriptor] = []
    day_start = start_open_time.replace(hour=0, minute=0)
    while day_start < end_open_time:
        day_end = day_start + timedelta(days=1)
        if day_end <= now and day_start < end_open_time and day_end > start_open_time:
            descriptors.append(
                build_archive_descriptor(
                    symbol=symbol,
                    granularity="daily",
                    period_start=day_start,
                )
            )
        day_start += timedelta(days=1)
    return descriptors


def _next_month(period_start: datetime) -> datetime:
    if period_start.month == 12:
        return period_start.replace(
            year=period_start.year + 1,
            month=1,
            day=1,
        )
    return period_start.replace(month=period_start.month + 1, day=1)


def _normalize_minute(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Archive periods must use timezone-aware UTC timestamps.")
    normalized = value.astimezone(UTC)
    if normalized.second or normalized.microsecond:
        raise ValueError("Archive periods must align to a UTC minute.")
    return normalized


def _timestamp_unit(period_start: datetime) -> timedelta:
    return (
        timedelta(milliseconds=1)
        if period_start < ARCHIVE_TIMESTAMP_SWITCH
        else timedelta(microseconds=1)
    )


def _archive_timestamp(value: str, unit: timedelta) -> datetime:
    try:
        raw_value = int(value)
    except (TypeError, ValueError) as error:
        raise BinanceArchiveError("archive_timestamp_invalid") from error
    if raw_value < 0 or str(raw_value) != value:
        raise BinanceArchiveError("archive_timestamp_invalid")
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    return epoch + raw_value * unit


def _archive_price(value: str) -> Decimal:
    parsed = _archive_decimal(value, "archive_price_invalid")
    if parsed <= 0:
        raise BinanceArchiveError("archive_price_invalid")
    return parsed


def _archive_nonnegative_decimal(value: str) -> Decimal:
    parsed = _archive_decimal(value, "archive_volume_invalid")
    if parsed < 0:
        raise BinanceArchiveError("archive_volume_invalid")
    return parsed


def _archive_decimal(value: str, category: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise BinanceArchiveError(category) from error
    if not parsed.is_finite():
        raise BinanceArchiveError(category)
    return parsed


def _archive_nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise BinanceArchiveError("archive_integer_invalid") from error
    if parsed < 0 or str(parsed) != value:
        raise BinanceArchiveError("archive_integer_invalid")
    return parsed
