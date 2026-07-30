import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.alert_event import AlertEvent


def build_price_cross_trigger_identity(*, symbol: str, provider_event_id: int) -> str:
    return f"binance:spot:{symbol}:aggTrade:{provider_event_id}"


async def create_alert_event(
    session: AsyncSession,
    *,
    alert_id: uuid.UUID,
    user_id: uuid.UUID,
    telegram_connection_id: uuid.UUID,
    exchange: str,
    market_type: str,
    symbol: str,
    base_asset: str,
    quote_asset: str,
    direction: str,
    target_price: Decimal,
    trigger_price: Decimal,
    provider_event_id: int,
    provider_event_time: datetime,
    observed_at: datetime,
    observed_after_reconnect: bool,
) -> AlertEvent:
    event = AlertEvent(
        alert_id=alert_id,
        user_id=user_id,
        telegram_connection_id=telegram_connection_id,
        event_type="price_crossed",
        trigger_identity=build_price_cross_trigger_identity(
            symbol=symbol,
            provider_event_id=provider_event_id,
        ),
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
        base_asset=base_asset,
        quote_asset=quote_asset,
        direction=direction,
        target_price=target_price,
        trigger_price=trigger_price,
        provider_event_id=provider_event_id,
        provider_event_time=provider_event_time,
        observed_at=observed_at,
        observed_after_reconnect=observed_after_reconnect,
    )
    session.add(event)
    await session.flush()
    return event


async def get_alert_event_for_alert(
    session: AsyncSession,
    *,
    alert_id: uuid.UUID,
) -> AlertEvent | None:
    return await session.scalar(select(AlertEvent).where(AlertEvent.alert_id == alert_id))
