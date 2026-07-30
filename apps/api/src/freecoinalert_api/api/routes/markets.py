from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.core.config import Settings, get_settings
from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.db.session import get_database_session
from freecoinalert_api.market_data.catalog import is_market_ready, list_safe_markets, utc_now
from freecoinalert_api.schemas.markets import (
    MarketEnvelope,
    MarketPriceRulesResponse,
    MarketResponse,
)

markets_router = APIRouter(tags=["markets"])


@markets_router.get("/markets")
async def list_markets(
    database_session: AsyncSession = Depends(get_database_session),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    current_time = utc_now()
    markets = await list_safe_markets(database_session)
    response_body = MarketEnvelope(
        markets=[
            market_response(
                market,
                current_time=current_time,
                max_age_seconds=settings.market_catalog_max_age_seconds,
            )
            for market in markets
        ]
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_body.model_dump(mode="json", by_alias=True),
        headers={"Cache-Control": "public, max-age=60"},
    )


def market_response(
    market: SupportedMarket,
    *,
    current_time: datetime,
    max_age_seconds: int,
) -> MarketResponse:
    available = is_market_ready(
        market,
        current_time=current_time,
        max_age_seconds=max_age_seconds,
    )
    price_rules = None

    if available:
        price_rules = MarketPriceRulesResponse(
            minimum=canonical_decimal_string(market.min_price),
            maximum=canonical_decimal_string(market.max_price),
            tick=canonical_decimal_string(market.price_tick),
        )

    return MarketResponse(
        exchange="binance",
        market_type="spot",
        symbol=market.symbol,
        base_asset=market.base_asset,
        quote_asset=market.quote_asset,
        status="available" if available else "unavailable",
        price_rules=price_rules,
        metadata_checked_at=market.metadata_checked_at,
    )


def canonical_decimal_string(value: Decimal | None) -> str:
    if value is None:
        raise ValueError("A ready market must have complete price rules.")

    return format(value, "f")
