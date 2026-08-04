from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.core.config import get_authentication_settings
from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.db.repositories.supported_markets import (
    get_alert_creation_ready_market,
    list_product_markets,
    upsert_catalog_metadata,
)

SUPPORTED_EXCHANGE = "binance"
SUPPORTED_MARKET_TYPE = "spot"
SUPPORTED_QUOTE_ASSET = "USDT"
SUPPORTED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT")

ProviderStatus = Literal[
    "pending_metadata",
    "trading",
    "halt",
    "break",
    "unsupported",
    "metadata_error",
]


class CatalogValidationError(Exception):
    pass


@dataclass(frozen=True)
class CatalogMetadata:
    base_asset: str | None
    quote_asset: str | None
    provider_status: ProviderStatus
    min_price: Decimal | None
    max_price: Decimal | None
    price_tick: Decimal | None
    metadata_checked_at: datetime
    status_reason: str | None


def parse_catalog_metadata(
    payload: dict[str, object],
    *,
    checked_at: datetime,
) -> dict[str, CatalogMetadata]:
    raw_symbols = payload.get("symbols")

    if not isinstance(raw_symbols, list):
        raise CatalogValidationError("The provider response did not contain a symbol list.")

    provider_symbols: dict[str, dict[str, object]] = {}

    for raw_symbol in raw_symbols:
        if not isinstance(raw_symbol, dict):
            raise CatalogValidationError("The provider response contained an invalid symbol entry.")

        symbol = raw_symbol.get("symbol")

        if not isinstance(symbol, str):
            raise CatalogValidationError("The provider response contained a symbol without an identifier.")

        if symbol in provider_symbols:
            raise CatalogValidationError("The provider response contained duplicate symbol metadata.")

        provider_symbols[symbol] = raw_symbol

    unexpected_symbols = set(provider_symbols) - set(SUPPORTED_SYMBOLS)

    if unexpected_symbols:
        raise CatalogValidationError("The provider response exceeded the approved symbol allowlist.")

    return {
        symbol: parse_symbol_metadata(provider_symbols.get(symbol), checked_at=checked_at)
        for symbol in SUPPORTED_SYMBOLS
    }


def parse_symbol_metadata(
    raw_symbol: dict[str, object] | None,
    *,
    checked_at: datetime,
) -> CatalogMetadata:
    if raw_symbol is None:
        return unavailable_metadata("unsupported", "symbol_missing", checked_at)

    symbol = raw_symbol.get("symbol")
    base_asset = raw_symbol.get("baseAsset")
    quote_asset = raw_symbol.get("quoteAsset")
    provider_status = raw_symbol.get("status")

    if not isinstance(symbol, str) or symbol not in SUPPORTED_SYMBOLS:
        raise CatalogValidationError("The provider symbol is not in the approved allowlist.")

    if not isinstance(base_asset, str) or not isinstance(quote_asset, str):
        return unavailable_metadata("unsupported", "asset_metadata_invalid", checked_at)

    if quote_asset != SUPPORTED_QUOTE_ASSET:
        return unavailable_metadata("unsupported", "quote_asset_unsupported", checked_at)

    if provider_status == "HALT":
        return unavailable_metadata("halt", "provider_halt", checked_at, base_asset, quote_asset)

    if provider_status == "BREAK":
        return unavailable_metadata("break", "provider_break", checked_at, base_asset, quote_asset)

    if provider_status != "TRADING":
        return unavailable_metadata("unsupported", "provider_status_unsupported", checked_at, base_asset, quote_asset)

    if not is_spot_trading_allowed(raw_symbol):
        return unavailable_metadata("unsupported", "spot_trading_not_allowed", checked_at, base_asset, quote_asset)

    try:
        min_price, max_price, price_tick = parse_price_filter(raw_symbol)
    except CatalogValidationError:
        return unavailable_metadata("metadata_error", "price_filter_invalid", checked_at, base_asset, quote_asset)

    if price_tick is None or price_tick <= 0:
        return unavailable_metadata("metadata_error", "price_tick_unavailable", checked_at, base_asset, quote_asset)

    return CatalogMetadata(
        base_asset=base_asset,
        quote_asset=quote_asset,
        provider_status="trading",
        min_price=min_price,
        max_price=max_price,
        price_tick=price_tick,
        metadata_checked_at=checked_at,
        status_reason=None,
    )


def unavailable_metadata(
    provider_status: ProviderStatus,
    status_reason: str,
    checked_at: datetime,
    base_asset: str | None = None,
    quote_asset: str | None = None,
) -> CatalogMetadata:
    return CatalogMetadata(
        base_asset=base_asset,
        quote_asset=quote_asset,
        provider_status=provider_status,
        min_price=None,
        max_price=None,
        price_tick=None,
        metadata_checked_at=checked_at,
        status_reason=status_reason,
    )


def is_spot_trading_allowed(raw_symbol: dict[str, object]) -> bool:
    value = raw_symbol.get("isSpotTradingAllowed")

    if isinstance(value, bool):
        return value

    permissions = raw_symbol.get("permissions")
    return isinstance(permissions, list) and "SPOT" in permissions


def parse_price_filter(raw_symbol: dict[str, object]) -> tuple[Decimal | None, Decimal | None, Decimal]:
    raw_filters = raw_symbol.get("filters")

    if not isinstance(raw_filters, list):
        raise CatalogValidationError("The provider symbol is missing filters.")

    price_filter: dict[str, object] | None = None

    for raw_filter in raw_filters:
        if isinstance(raw_filter, dict) and raw_filter.get("filterType") == "PRICE_FILTER":
            price_filter = raw_filter
            break

    if price_filter is None:
        raise CatalogValidationError("The provider symbol is missing PRICE_FILTER.")

    minimum = parse_provider_decimal(price_filter.get("minPrice"))
    maximum = parse_provider_decimal(price_filter.get("maxPrice"))
    tick = parse_provider_decimal(price_filter.get("tickSize"))

    if maximum != Decimal("0") and minimum != Decimal("0") and maximum < minimum:
        raise CatalogValidationError("The provider price bounds are invalid.")

    return (
        None if minimum == Decimal("0") else minimum,
        None if maximum == Decimal("0") else maximum,
        tick,
    )


def parse_provider_decimal(value: object) -> Decimal:
    if not isinstance(value, str) or value.strip() != value or value == "":
        raise CatalogValidationError("The provider decimal value is invalid.")

    try:
        decimal_value = Decimal(value)
    except InvalidOperation as error:
        raise CatalogValidationError("The provider decimal value is invalid.") from error

    if not decimal_value.is_finite() or decimal_value < 0:
        raise CatalogValidationError("The provider decimal value is invalid.")

    exponent = decimal_value.as_tuple().exponent

    if exponent < -18 or decimal_value.adjusted() >= 20:
        raise CatalogValidationError("The provider decimal precision exceeds NUMERIC(38,18).")

    return decimal_value


async def list_safe_markets(
    session: AsyncSession,
) -> list[SupportedMarket]:
    return list(await list_product_markets(session))


async def get_ready_market(
    session: AsyncSession,
    *,
    symbol: str,
    current_time: datetime,
    max_age_seconds: int,
) -> SupportedMarket | None:
    return await get_alert_creation_ready_market(
        session,
        exchange=SUPPORTED_EXCHANGE,
        market_type=SUPPORTED_MARKET_TYPE,
        symbol=symbol,
        current_time=current_time,
        max_age_seconds=max_age_seconds,
    )


async def save_catalog_metadata(
    session: AsyncSession,
    *,
    metadata_by_symbol: dict[str, CatalogMetadata],
) -> None:
    await upsert_catalog_metadata(session, metadata_by_symbol=metadata_by_symbol)


def utc_now() -> datetime:
    settings = get_authentication_settings()
    if settings.e2e_test_mode and settings.e2e_clock_now is not None:
        return settings.e2e_clock_now
    return datetime.now(UTC)


def is_market_ready(
    market: SupportedMarket,
    *,
    current_time: datetime,
    max_age_seconds: int,
) -> bool:
    return (
        market.product_enabled
        and market.provider_status == "trading"
        and market.metadata_checked_at is not None
        and market.metadata_checked_at >= current_time - timedelta(seconds=max_age_seconds)
        and market.min_price is not None
        and market.max_price is not None
        and market.price_tick is not None
        and market.price_tick > 0
    )
