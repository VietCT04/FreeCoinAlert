"""Correction boundary for rebuilding global signal-event history."""

from uuid import UUID

from freecoinalert_api.db.repositories.signal_evaluation_states import (
    get_or_create_evaluation_state_for_update,
    mark_evaluation_state,
)
from freecoinalert_api.db.session import get_async_session_factory


async def mark_correction_rebuild_required(
    *,
    supported_market_id: UUID,
    signal_preset_id: UUID,
) -> None:
    """Suspend a key until the canonical-history rebuild replaces its state.

    Signal events are immutable, so correction processing never edits or deletes an
    occurrence. The explicit historical rebuild inserts replacement revisions and
    invalidation records as needed.
    """
    async with get_async_session_factory()() as session:
        async with session.begin():
            state = await get_or_create_evaluation_state_for_update(
                session,
                supported_market_id=supported_market_id,
                signal_preset_id=signal_preset_id,
            )
            mark_evaluation_state(
                state,
                status="stale",
                reason="candle_correction_rebuild_required",
            )
