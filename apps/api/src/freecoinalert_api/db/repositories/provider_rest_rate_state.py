from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.provider_rest_rate_state import ProviderRestRateState


async def lock_provider_rest_rate_state(
    session: AsyncSession,
    *,
    provider_key: str,
    now: datetime,
) -> ProviderRestRateState:
    now = now.astimezone(UTC)
    window_started_at = now.replace(second=0, microsecond=0)
    statement = insert(ProviderRestRateState).values(
        provider_key=provider_key,
        window_started_at=window_started_at,
        reserved_weight=0,
        provider_used_weight=0,
        provider_limit_weight=None,
        blocked_until=None,
        blocked_reason=None,
        last_response_at=None,
    )
    await session.execute(
        statement.on_conflict_do_nothing(
            index_elements=[ProviderRestRateState.provider_key]
        )
    )
    state = await session.scalar(
        select(ProviderRestRateState)
        .where(ProviderRestRateState.provider_key == provider_key)
        .with_for_update()
    )
    if state is None:
        raise RuntimeError("The provider REST rate state row could not be locked.")

    if state.window_started_at.astimezone(UTC) != window_started_at:
        state.window_started_at = window_started_at
        state.reserved_weight = 0
        state.provider_used_weight = 0

    return state
