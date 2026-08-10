"""Resumable, side-effect-free import of validated Binance candle archives."""

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from freecoinalert_api.db.repositories.candle_backfill_checkpoints import (
    advance_checkpoint,
    ensure_checkpoint,
    get_checkpoint,
    mark_checkpoint_complete,
    mark_checkpoint_failed,
    record_verified_checksum,
    start_checkpoint_attempt,
)
from freecoinalert_api.db.repositories.market_candles import get_complete_candle_coverage
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.binance_public_data import (
    BinanceArchiveCandidate,
    BinanceArchiveDescriptor,
    BinanceArchiveError,
    BinancePublicDataArchiveClient,
    DownloadedBinanceArchive,
    parse_and_validate_archive,
)
from freecoinalert_api.market_data.candles.ingestion import CandleIngestionService


logger = logging.getLogger(__name__)
ARCHIVE_CHUNK_CANDLE_COUNT = 10_080


@dataclass(frozen=True, slots=True)
class ArchiveImportResult:
    archive_key: str
    status: str
    row_count: int
    committed_row_count: int
    checksum_sha256: str | None
    next_open_time: datetime


class BinanceCandleArchiveImporter:
    """Import one planned archive; the #159 worker owns scheduling this primitive."""

    def __init__(
        self,
        *,
        client: BinancePublicDataArchiveClient,
        ingestion: CandleIngestionService | None = None,
    ) -> None:
        self._client = client
        self._ingestion = ingestion or CandleIngestionService()

    async def import_candidate(
        self,
        *,
        candidate: BinanceArchiveCandidate,
        supported_market_id: UUID,
    ) -> ArchiveImportResult:
        self._log_planned(candidate.primary)
        try:
            return await self.import_archive(
                descriptor=candidate.primary,
                supported_market_id=supported_market_id,
            )
        except BinanceArchiveError as error:
            if error.category != "archive_not_available" or not candidate.daily_fallbacks:
                raise
            for fallback in candidate.daily_fallbacks:
                if await self._checkpoint_is_complete(fallback.archive_key):
                    continue
                self._log_planned(fallback)
                try:
                    return await self.import_archive(
                        descriptor=fallback,
                        supported_market_id=supported_market_id,
                    )
                except BinanceArchiveError as fallback_error:
                    if fallback_error.category != "archive_not_available":
                        raise
            raise error

    @staticmethod
    async def _checkpoint_is_complete(archive_key: str) -> bool:
        async with get_async_session_factory()() as session:
            checkpoint = await get_checkpoint(session, archive_key=archive_key)
            return checkpoint is not None and checkpoint.status == "complete"

    async def import_archive(
        self,
        *,
        descriptor: BinanceArchiveDescriptor,
        supported_market_id: UUID,
    ) -> ArchiveImportResult:
        started = time.monotonic()
        checkpoint = await self._start_attempt(descriptor, supported_market_id)
        if checkpoint.status == "complete":
            return ArchiveImportResult(
                archive_key=descriptor.archive_key,
                status="complete",
                row_count=0,
                committed_row_count=0,
                checksum_sha256=checkpoint.checksum_sha256,
                next_open_time=checkpoint.next_open_time,
            )
        if checkpoint.next_open_time > descriptor.period_start:
            logger.info(
                "market.candle.archive.resumed symbol=%s granularity=%s period=%s/%s "
                "archive_key=%s next_open_time=%s attempt=%s",
                descriptor.symbol,
                descriptor.granularity,
                descriptor.period_start,
                descriptor.period_end,
                descriptor.archive_key,
                checkpoint.next_open_time,
                checkpoint.attempt_count,
            )

        logger.info(
            "market.candle.archive.download_started symbol=%s granularity=%s period=%s/%s "
            "archive_key=%s attempt=%s",
            descriptor.symbol,
            descriptor.granularity,
            descriptor.period_start,
            descriptor.period_end,
            descriptor.archive_key,
            checkpoint.attempt_count,
        )
        downloaded: DownloadedBinanceArchive | None = None
        try:
            downloaded = await self._client.download(descriptor)
            if (
                checkpoint.checksum_sha256 is not None
                and checkpoint.checksum_sha256 != downloaded.checksum_sha256
            ):
                raise BinanceArchiveError("archive_checksum_changed")
            await self._record_checksum(descriptor, downloaded.checksum_sha256)
            rows = parse_and_validate_archive(
                downloaded,
                supported_market_id=supported_market_id,
            )
            logger.info(
                "market.candle.archive.validated symbol=%s granularity=%s period=%s/%s "
                "archive_key=%s row_count=%s checksum_sha256=%s attempt=%s",
                descriptor.symbol,
                descriptor.granularity,
                descriptor.period_start,
                descriptor.period_end,
                descriptor.archive_key,
                len(rows),
                downloaded.checksum_sha256,
                checkpoint.attempt_count,
            )
            committed_row_count = await self._persist_chunks(descriptor, rows)
            completed = await self._complete_checkpoint(descriptor, supported_market_id)
            logger.info(
                "market.candle.archive.completed symbol=%s granularity=%s period=%s/%s "
                "archive_key=%s row_count=%s next_open_time=%s attempt=%s duration_seconds=%.3f",
                descriptor.symbol,
                descriptor.granularity,
                descriptor.period_start,
                descriptor.period_end,
                descriptor.archive_key,
                len(rows),
                completed.next_open_time,
                completed.attempt_count,
                time.monotonic() - started,
            )
            return ArchiveImportResult(
                archive_key=descriptor.archive_key,
                status=completed.status,
                row_count=len(rows),
                committed_row_count=committed_row_count,
                checksum_sha256=downloaded.checksum_sha256,
                next_open_time=completed.next_open_time,
            )
        except BinanceArchiveError as error:
            if error.category.startswith("checksum"):
                logger.warning(
                    "market.candle.archive.checksum_failed symbol=%s granularity=%s "
                    "period=%s/%s archive_key=%s category=%s attempt=%s",
                    descriptor.symbol,
                    descriptor.granularity,
                    descriptor.period_start,
                    descriptor.period_end,
                    descriptor.archive_key,
                    error.category,
                    checkpoint.attempt_count,
                )
            await self._fail_checkpoint(descriptor, error.category)
            logger.warning(
                "market.candle.archive.failed symbol=%s granularity=%s period=%s/%s "
                "archive_key=%s category=%s attempt=%s duration_seconds=%.3f",
                descriptor.symbol,
                descriptor.granularity,
                descriptor.period_start,
                descriptor.period_end,
                descriptor.archive_key,
                error.category,
                checkpoint.attempt_count,
                time.monotonic() - started,
            )
            raise
        except Exception as error:
            category = "canonical_persistence_failed"
            await self._fail_checkpoint(descriptor, category)
            logger.exception(
                "market.candle.archive.failed symbol=%s granularity=%s period=%s/%s "
                "archive_key=%s category=%s attempt=%s duration_seconds=%.3f",
                descriptor.symbol,
                descriptor.granularity,
                descriptor.period_start,
                descriptor.period_end,
                descriptor.archive_key,
                category,
                checkpoint.attempt_count,
                time.monotonic() - started,
            )
            raise error
        finally:
            if downloaded is not None:
                downloaded.close()

    async def _start_attempt(self, descriptor: BinanceArchiveDescriptor, market_id: UUID):
        async with get_async_session_factory()() as session:
            async with session.begin():
                checkpoint = await ensure_checkpoint(
                    session,
                    supported_market_id=market_id,
                    archive_granularity=descriptor.granularity,
                    period_start=descriptor.period_start,
                    period_end=descriptor.period_end,
                    archive_key=descriptor.archive_key,
                )
                await start_checkpoint_attempt(
                    session,
                    checkpoint=checkpoint,
                    started_at=datetime.now(UTC),
                )
                return checkpoint

    async def _record_checksum(self, descriptor: BinanceArchiveDescriptor, checksum: str) -> None:
        async with get_async_session_factory()() as session:
            async with session.begin():
                checkpoint = await get_checkpoint(
                    session,
                    archive_key=descriptor.archive_key,
                    for_update=True,
                )
                if checkpoint is None:
                    raise ValueError("Archive checkpoint disappeared during import.")
                await record_verified_checksum(
                    session,
                    checkpoint=checkpoint,
                    checksum_sha256=checksum,
                )

    async def _persist_chunks(
        self,
        descriptor: BinanceArchiveDescriptor,
        rows: Sequence,
    ) -> int:
        committed_row_count = 0
        offset = 0
        while offset < len(rows):
            chunk = rows[offset : offset + ARCHIVE_CHUNK_CANDLE_COUNT]
            async with get_async_session_factory()() as session:
                async with session.begin():
                    checkpoint = await get_checkpoint(
                        session,
                        archive_key=descriptor.archive_key,
                        for_update=True,
                    )
                    if checkpoint is None:
                        raise ValueError("Archive checkpoint disappeared during import.")
                    if checkpoint.status == "complete":
                        return committed_row_count
                    pending = [
                        row for row in chunk if row.open_time >= checkpoint.next_open_time
                    ]
                    if not pending:
                        offset += len(chunk)
                        continue
                    result = await self._ingestion.persist_canonical_candles_in_session(
                        session,
                        pending,
                    )
                    next_open_time = pending[-1].open_time + timedelta(minutes=1)
                    await advance_checkpoint(
                        session,
                        checkpoint=checkpoint,
                        next_open_time=next_open_time,
                    )
                    committed_row_count += len(pending)
                    logger.info(
                        "market.candle.archive.chunk_committed symbol=%s granularity=%s "
                        "period=%s/%s archive_key=%s row_count=%s changed_count=%s "
                        "next_open_time=%s attempt=%s",
                        descriptor.symbol,
                        descriptor.granularity,
                        descriptor.period_start,
                        descriptor.period_end,
                        descriptor.archive_key,
                        len(pending),
                        result.changed_count,
                        checkpoint.next_open_time,
                        checkpoint.attempt_count,
                    )
            offset += len(chunk)
        return committed_row_count

    async def _complete_checkpoint(
        self,
        descriptor: BinanceArchiveDescriptor,
        supported_market_id: UUID,
    ):
        async with get_async_session_factory()() as session:
            async with session.begin():
                checkpoint = await get_checkpoint(
                    session,
                    archive_key=descriptor.archive_key,
                    for_update=True,
                )
                if checkpoint is None:
                    raise ValueError("Archive checkpoint disappeared during import.")
                coverage = await get_complete_candle_coverage(
                    session,
                    supported_market_id=supported_market_id,
                    timeframe="1m",
                    start_open_time=descriptor.period_start,
                    end_open_time=descriptor.period_end,
                )
                if not coverage.is_complete:
                    await mark_checkpoint_failed(
                        session,
                        checkpoint=checkpoint,
                        category="coverage_incomplete",
                    )
                    raise BinanceArchiveError("coverage_incomplete")
                await mark_checkpoint_complete(
                    session,
                    checkpoint=checkpoint,
                    completed_at=datetime.now(UTC),
                )
                return checkpoint

    async def _fail_checkpoint(self, descriptor: BinanceArchiveDescriptor, category: str) -> None:
        async with get_async_session_factory()() as session:
            async with session.begin():
                checkpoint = await get_checkpoint(
                    session,
                    archive_key=descriptor.archive_key,
                    for_update=True,
                )
                if checkpoint is not None and checkpoint.status != "complete":
                    await mark_checkpoint_failed(
                        session,
                        checkpoint=checkpoint,
                        category=category,
                    )

    def _log_planned(self, descriptor: BinanceArchiveDescriptor) -> None:
        logger.info(
            "market.candle.archive.planned symbol=%s granularity=%s period=%s/%s "
            "archive_key=%s",
            descriptor.symbol,
            descriptor.granularity,
            descriptor.period_start,
            descriptor.period_end,
            descriptor.archive_key,
        )
