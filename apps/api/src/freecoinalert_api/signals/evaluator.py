import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from freecoinalert_api.db.models.candle_symbol_state import CandleSymbolState
from freecoinalert_api.db.models.market_candle import MarketCandle
from freecoinalert_api.db.models.signal_preset import SignalPreset
from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.db.repositories.signal_evaluation_states import (
    get_or_create_evaluation_state_for_update,
    mark_evaluation_state,
)
from freecoinalert_api.db.repositories.signal_events import create_signal_event
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.events import ConfirmedCandleEvent
from freecoinalert_api.signals.calculations import PresetCalculation, calculate_preset
from freecoinalert_api.signals.crossings import crosses, relation

logger = logging.getLogger(__name__)
UNSAFE_CANDLE_STATUSES = {"stale", "gapped", "error"}


class PresetSignalEvaluator:
    async def handle_confirmed_candle(self, event: ConfirmedCandleEvent) -> None:
        if event.timeframe not in {"1h", "4h"}:
            return
        cache: dict[object, PresetCalculation] = {}
        async with get_async_session_factory()() as session:
            async with session.begin():
                candle = await session.get(MarketCandle, event.candle_id)
                if candle is None or not candle.is_current or candle.status != "complete":
                    return
                if candle.revision != event.candle_revision:
                    return
                candle_state = await session.get(CandleSymbolState, candle.supported_market_id)
                presets = await self._presets(session, candle.timeframe)
                if candle_state is not None and candle_state.status in UNSAFE_CANDLE_STATUSES:
                    for preset in presets:
                        state = await get_or_create_evaluation_state_for_update(
                            session,
                            supported_market_id=candle.supported_market_id,
                            signal_preset_id=preset.id,
                        )
                        mark_evaluation_state(state, status="stale", reason="candle_data_unsafe")
                    logger.warning("signal.evaluation.data_stale market_id=%s", candle.supported_market_id)
                    return
                market = await session.get(SupportedMarket, candle.supported_market_id)
                if market is None or market.base_asset is None or market.quote_asset is None:
                    return
                for preset in presets:
                    calculation = await calculate_preset(
                        session,
                        preset=preset,
                        candle=candle,
                        cache=cache,  # type: ignore[arg-type]
                    )
                    await self._evaluate_preset(
                        session=session,
                        market=market,
                        candle=candle,
                        preset=preset,
                        calculation=calculation,
                        backfilled=False,
                    )

    async def _presets(self, session: object, timeframe: str) -> list[SignalPreset]:
        statement = select(SignalPreset).where(
            SignalPreset.timeframe == timeframe,
            SignalPreset.status.in_(("active", "superseded")),
        )
        return list((await session.scalars(statement)).all())  # type: ignore[union-attr]

    async def _evaluate_preset(
        self,
        *,
        session: object,
        market: SupportedMarket,
        candle: MarketCandle,
        preset: SignalPreset,
        calculation: PresetCalculation,
        backfilled: bool,
    ) -> None:
        state = await get_or_create_evaluation_state_for_update(  # type: ignore[arg-type]
            session,
            supported_market_id=candle.supported_market_id,
            signal_preset_id=preset.id,
        )
        if state.status == "disabled":
            return
        if state.last_candle_id == candle.id and state.last_candle_revision == candle.revision:
            return
        if state.last_candle_open_time is not None and candle.open_time < state.last_candle_open_time:
            return
        if calculation.status != "success" or calculation.left_value is None or calculation.right_value is None:
            mark_evaluation_state(state, status="warming", reason=calculation.status)
            logger.info("signal.evaluation.insufficient_history market_id=%s preset_id=%s", market.id, preset.id)
            return
        if state.last_candle_open_time == candle.open_time and state.last_candle_revision is not None:
            mark_evaluation_state(state, status="stale", reason="candle_correction_rebuild_required")
            return
        if state.last_relation is None or state.last_left_value is None or state.last_right_value is None:
            self._store_state(state, candle, calculation)
            state.initialized_at = datetime.now(UTC)
            logger.info("signal.evaluation.initialized market_id=%s preset_id=%s", market.id, preset.id)
            return
        triggered = crosses(
            direction=preset.direction,
            previous_left_value=state.last_left_value,
            previous_right_value=state.last_right_value,
            current_left_value=calculation.left_value,
            current_right_value=calculation.right_value,
        )
        if triggered:
            inserted = await create_signal_event(  # type: ignore[arg-type]
                session,
                values=self._event_values(market, candle, preset, state.last_left_value, state.last_right_value, calculation, backfilled),
            )
            if inserted:
                logger.info("signal.event.created market_id=%s preset_id=%s candle_id=%s", market.id, preset.id, candle.id)
            else:
                logger.info("signal.event.duplicate_suppressed market_id=%s preset_id=%s candle_id=%s", market.id, preset.id, candle.id)
        self._store_state(state, candle, calculation)
        logger.info("signal.evaluation.succeeded market_id=%s preset_id=%s", market.id, preset.id)

    def _store_state(self, state: object, candle: MarketCandle, calculation: PresetCalculation) -> None:
        state.status = "ready"  # type: ignore[attr-defined]
        state.status_reason = None  # type: ignore[attr-defined]
        state.last_candle_id = candle.id  # type: ignore[attr-defined]
        state.last_candle_revision = candle.revision  # type: ignore[attr-defined]
        state.last_candle_open_time = candle.open_time  # type: ignore[attr-defined]
        state.last_relation = relation(calculation.left_value, calculation.right_value)  # type: ignore[arg-type,attr-defined]
        state.last_left_value = calculation.left_value  # type: ignore[attr-defined]
        state.last_right_value = calculation.right_value  # type: ignore[attr-defined]
        state.calculation_state = calculation.calculation_state  # type: ignore[attr-defined]

    def _event_values(self, market: SupportedMarket, candle: MarketCandle, preset: SignalPreset, previous_left: Decimal, previous_right: Decimal, calculation: PresetCalculation, backfilled: bool) -> dict[str, object]:
        open_time_ms = int(candle.open_time.astimezone(UTC).timestamp() * 1000)
        trigger_identity = f"{market.exchange}:{market.market_type}:{market.symbol}:{preset.timeframe}:{preset.code}:v{preset.version}:{open_time_ms}:r{candle.revision}"
        return {
            "supported_market_id": market.id, "signal_preset_id": preset.id, "trigger_candle_id": candle.id,
            "event_type": "preset_crossed", "trigger_identity": trigger_identity,
            "exchange_snapshot": market.exchange, "market_type_snapshot": market.market_type,
            "symbol_snapshot": market.symbol, "base_asset_snapshot": market.base_asset,
            "quote_asset_snapshot": market.quote_asset, "preset_code_snapshot": preset.code,
            "preset_version_snapshot": preset.version, "preset_name_snapshot": preset.name,
            "strategy_type_snapshot": preset.strategy_type,
            "calculation_version_snapshot": calculation.key.calculation_version,
            "timeframe_snapshot": preset.timeframe, "direction_snapshot": preset.direction,
            "period_snapshot": preset.period, "threshold_snapshot": preset.threshold,
            "price_input_snapshot": preset.price_input, "candle_revision": candle.revision,
            "candle_open_time": candle.open_time, "candle_close_time": candle.close_time,
            "previous_left_value": previous_left, "previous_right_value": previous_right,
            "current_left_value": calculation.left_value, "current_right_value": calculation.right_value,
            "candle_close_price": candle.close_price, "backfilled": backfilled,
            "occurred_at": candle.close_time,
        }
