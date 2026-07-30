from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_preset import SignalPreset


async def list_active_presets(session: AsyncSession) -> Sequence[SignalPreset]:
    statement = select(SignalPreset).where(SignalPreset.status == "active").order_by(
        SignalPreset.timeframe,
        SignalPreset.strategy_type,
        SignalPreset.direction,
        SignalPreset.code,
    )
    return (await session.scalars(statement)).all()


async def get_active_preset_by_code_version(
    session: AsyncSession,
    *,
    code: str,
    version: int,
) -> SignalPreset | None:
    return await session.scalar(
        select(SignalPreset).where(
            SignalPreset.code == code,
            SignalPreset.version == version,
            SignalPreset.status == "active",
        )
    )


async def get_preset_by_code_version(
    session: AsyncSession,
    *,
    code: str,
    version: int,
) -> SignalPreset | None:
    return await session.scalar(
        select(SignalPreset).where(
            SignalPreset.code == code,
            SignalPreset.version == version,
        )
    )


async def list_all_presets_for_evaluation(session: AsyncSession) -> Sequence[SignalPreset]:
    return (await session.scalars(select(SignalPreset).where(SignalPreset.status != "disabled"))).all()
