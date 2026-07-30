import asyncio
import logging
import time

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.repositories.supported_markets import (
    mark_catalog_sync_failure,
    upsert_catalog_metadata,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.binance_rest import (
    BinanceMetadataError,
    BinancePublicMarketDataClient,
)
from freecoinalert_api.market_data.catalog import (
    CatalogValidationError,
    SUPPORTED_EXCHANGE,
    SUPPORTED_MARKET_TYPE,
    SUPPORTED_SYMBOLS,
    parse_catalog_metadata,
    utc_now,
)

logger = logging.getLogger(__name__)


async def synchronize_catalog() -> int:
    settings = get_settings()
    started_at = time.monotonic()
    logger.info(
        "market.catalog.sync_started exchange=%s market_type=%s symbol_count=%s",
        SUPPORTED_EXCHANGE,
        SUPPORTED_MARKET_TYPE,
        len(SUPPORTED_SYMBOLS),
    )
    client = BinancePublicMarketDataClient(base_url=settings.binance_spot_base_url)

    try:
        payload = await client.get_spot_exchange_info(symbols=SUPPORTED_SYMBOLS)
        metadata_by_symbol = parse_catalog_metadata(payload, checked_at=utc_now())

        async with get_async_session_factory()() as session:
            async with session.begin():
                await upsert_catalog_metadata(session, metadata_by_symbol=metadata_by_symbol)
    except BinanceMetadataError as error:
        return report_sync_failure(
            error.category,
            started_at=started_at,
            retry_after_seconds=error.retry_after_seconds,
        )
    except CatalogValidationError:
        return report_sync_failure("metadata_invalid", started_at=started_at)
    except Exception:
        return report_sync_failure("persistence_unavailable", started_at=started_at)

    unavailable_count = sum(
        metadata.provider_status != "trading" for metadata in metadata_by_symbol.values()
    )
    duration_ms = int((time.monotonic() - started_at) * 1000)
    logger.info(
        "market.catalog.sync_succeeded exchange=%s market_type=%s row_count=%s "
        "unavailable_count=%s duration_ms=%s",
        SUPPORTED_EXCHANGE,
        SUPPORTED_MARKET_TYPE,
        len(metadata_by_symbol),
        unavailable_count,
        duration_ms,
    )

    for symbol, metadata in metadata_by_symbol.items():
        if metadata.provider_status != "trading":
            logger.warning(
                "market.catalog.symbol_unavailable exchange=%s market_type=%s symbol=%s "
                "provider_status=%s",
                SUPPORTED_EXCHANGE,
                SUPPORTED_MARKET_TYPE,
                symbol,
                metadata.provider_status,
            )

    return 0


def report_sync_failure(
    error_category: str,
    *,
    started_at: float,
    retry_after_seconds: int | None = None,
) -> int:
    mark_catalog_sync_failure(error_category=error_category)
    duration_ms = int((time.monotonic() - started_at) * 1000)
    logger.error(
        "market.catalog.sync_failed exchange=%s market_type=%s category=%s "
        "retry_after_seconds=%s duration_ms=%s",
        SUPPORTED_EXCHANGE,
        SUPPORTED_MARKET_TYPE,
        error_category,
        retry_after_seconds,
        duration_ms,
    )
    return 1


def main() -> None:
    raise SystemExit(asyncio.run(synchronize_catalog()))


if __name__ == "__main__":
    main()
