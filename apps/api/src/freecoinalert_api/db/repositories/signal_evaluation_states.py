from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_evaluation_state import SignalEvaluationState


async def get_or_create_evaluation_state_for_update(
    session: AsyncSession,
    *,
    supported_market_id: UUID,
    signal_preset_id: UUID,
) -> SignalEvaluationState:
    statement = insert(SignalEvaluationState).values(
        supported_market_id=supported_market_id,
        signal_preset_id=signal_preset_id,
        status="warming",
        calculation_state={},
    ).on_conflict_do_nothing(
        constraint="uq_signal_evaluation_states_market_preset"
    )
    await session.execute(statement)
    state = await session.scalar(
        select(SignalEvaluationState)
        .where(
            SignalEvaluationState.supported_market_id == supported_market_id,
            SignalEvaluationState.signal_preset_id == signal_preset_id,
        )
        .with_for_update()
    )
    if state is None:
        raise RuntimeError("Evaluation state was not created.")
    return state


async def list_evaluation_states(
    session: AsyncSession,
    *,
    statuses: tuple[str, ...] | None = None,
) -> list[SignalEvaluationState]:
    statement = select(SignalEvaluationState)
    if statuses is not None:
        statement = statement.where(SignalEvaluationState.status.in_(statuses))
    return list((await session.scalars(statement.order_by(SignalEvaluationState.updated_at))).all())


def mark_evaluation_state(
    state: SignalEvaluationState,
    *,
    status: str,
    reason: str | None,
) -> None:
    state.status = status
    state.status_reason = reason
    state.updated_at = datetime.now(UTC)
