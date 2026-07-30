from datetime import datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from freecoinalert_api.db.models.market_symbol_state import MarketSymbolState


async def upsert_market_symbol_state(
    session: AsyncSession,
    *,
    supported_market_id: UUID,
    status: str,
    last_provider_event_id: int | None,
    last_price: object | None,
    last_provider_trade_at: datetime | None,
    last_received_at: datetime | None,
    connection_generation: UUID | None,
    status_reason: str | None,
) -> None:
    statement = insert(MarketSymbolState).values(
        supported_market_id=supported_market_id,
        status=status,
        last_provider_event_id=last_provider_event_id,
        last_price=last_price,
        last_provider_trade_at=last_provider_trade_at,
        last_received_at=last_received_at,
        connection_generation=connection_generation,
        status_reason=status_reason,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[MarketSymbolState.supported_market_id],
        set_={
            "status": statement.excluded.status,
            "last_provider_event_id": statement.excluded.last_provider_event_id,
            "last_price": statement.excluded.last_price,
            "last_provider_trade_at": statement.excluded.last_provider_trade_at,
            "last_received_at": statement.excluded.last_received_at,
            "connection_generation": statement.excluded.connection_generation,
            "status_reason": statement.excluded.status_reason,
            "updated_at": func.now(),
        },
    )
    await session.execute(statement)
