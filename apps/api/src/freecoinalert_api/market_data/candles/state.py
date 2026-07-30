from datetime import UTC, datetime, timedelta

from freecoinalert_api.db.repositories.candle_operations import upsert_candle_symbol_state
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.events import ConfirmedCandleEvent


class CandleStateRecorder:
    def __init__(self, *, max_lag_seconds: int) -> None:
        self._max_lag_seconds = max_lag_seconds
        self._latest: dict[object, dict[str, datetime]] = {}

    async def handle_confirmed_candle(self, event: ConfirmedCandleEvent) -> None:
        timestamps = self._latest.setdefault(event.supported_market_id, {})
        timestamps[event.timeframe] = event.open_time
        expected = datetime.now(UTC).replace(second=0, microsecond=0) - timedelta(minutes=1)
        latest = timestamps.get("1m")
        status = "live" if latest is not None and (expected - latest).total_seconds() <= self._max_lag_seconds else "stale"
        async with get_async_session_factory()() as session:
            async with session.begin():
                await upsert_candle_symbol_state(
                    session,
                    supported_market_id=event.supported_market_id,
                    status=status,
                    latest_complete_1m_open_time=timestamps.get("1m"),
                    latest_complete_1h_open_time=timestamps.get("1h"),
                    latest_complete_4h_open_time=timestamps.get("4h"),
                    last_websocket_received_at=event.observed_at,
                    last_reconciled_through=None,
                    unresolved_gap_count=0,
                    status_reason=None if status == "live" else "candle_lag",
                )
