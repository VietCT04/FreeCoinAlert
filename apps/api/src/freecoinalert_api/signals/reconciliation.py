from sqlalchemy import select

from freecoinalert_api.db.models.signal_preset import SignalPreset
from freecoinalert_api.db.repositories.signal_evaluation_states import (
    list_evaluation_states,
    mark_evaluation_state,
)
from freecoinalert_api.db.session import get_async_session_factory


async def reconcile_disabled_presets() -> None:
    """Stop durable evaluation for presets disabled after state initialization."""
    async with get_async_session_factory()() as session:
        async with session.begin():
            states = await list_evaluation_states(session, statuses=("warming", "ready", "stale", "error"))
            preset_ids = {state.signal_preset_id for state in states}
            if not preset_ids:
                return
            disabled_ids = set(
                (await session.scalars(select(SignalPreset.id).where(SignalPreset.id.in_(preset_ids), SignalPreset.status == "disabled"))).all()
            )
            for state in states:
                if state.signal_preset_id in disabled_ids:
                    mark_evaluation_state(state, status="disabled", reason="preset_disabled")
