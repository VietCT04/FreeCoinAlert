from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.supported_market import SupportedMarket


class CatalogMetadata(Protocol):
    base_asset: str | None
    quote_asset: str | None
    provider_status: str
    min_price: Decimal | None
    max_price: Decimal | None
    price_tick: Decimal | None
    metadata_checked_at: datetime
    status_reason: str | None


async def list_product_markets(session: AsyncSession) -> Sequence[SupportedMarket]:
    statement = select(SupportedMarket).order_by(SupportedMarket.symbol)
    return (await session.scalars(statement)).all()


async def get_supported_market(
    session: AsyncSession,
    *,
    exchange: str,
    market_type: str,
    symbol: str,
    for_update: bool = False,
) -> SupportedMarket | None:
    statement = select(SupportedMarket).where(
        SupportedMarket.exchange == exchange,
        SupportedMarket.market_type == market_type,
        SupportedMarket.symbol == symbol,
    )

    if for_update:
        statement = statement.with_for_update()

    return await session.scalar(statement)


async def get_alert_creation_ready_market(
    session: AsyncSession,
    *,
    exchange: str,
    market_type: str,
    symbol: str,
    current_time: datetime,
    max_age_seconds: int,
) -> SupportedMarket | None:
    market = await get_supported_market(
        session,
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
    )

    if market is None or not market.product_enabled or market.provider_status != "trading":
        return None

    if (
        market.metadata_checked_at is None
        or market.metadata_checked_at < current_time - timedelta(seconds=max_age_seconds)
        or market.min_price is None
        or market.max_price is None
        or market.price_tick is None
        or market.price_tick <= 0
    ):
        return None

    return market


async def upsert_catalog_metadata(
    session: AsyncSession,
    *,
    metadata_by_symbol: dict[str, CatalogMetadata],
) -> None:
    statement = select(SupportedMarket).with_for_update().order_by(SupportedMarket.symbol)
    markets = (await session.scalars(statement)).all()

    if len(markets) != len(metadata_by_symbol):
        raise ValueError("The product market catalog does not match the approved allowlist.")

    for market in markets:
        metadata = metadata_by_symbol.get(market.symbol)

        if metadata is None:
            raise ValueError("The product market catalog does not match the approved allowlist.")

        previous_status = market.provider_status
        market.base_asset = metadata.base_asset
        market.quote_asset = metadata.quote_asset
        market.provider_status = metadata.provider_status
        market.min_price = metadata.min_price
        market.max_price = metadata.max_price
        market.price_tick = metadata.price_tick
        market.metadata_checked_at = metadata.metadata_checked_at
        market.status_reason = metadata.status_reason

        if metadata.provider_status == "trading":
            market.provider_disabled_at = None
            market.status_reason = None
        elif (
            previous_status == "trading"
            and metadata.provider_status in {"halt", "break", "unsupported"}
        ):
            market.provider_disabled_at = metadata.metadata_checked_at


def mark_catalog_sync_failure(*, error_category: str) -> None:
    del error_category
