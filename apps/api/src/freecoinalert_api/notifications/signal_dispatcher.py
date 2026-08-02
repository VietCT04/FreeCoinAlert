"""Fan out eligible signal occurrences into durable Telegram outbox jobs."""

import asyncio
import logging
import signal
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.core.config import get_settings
from freecoinalert_api.db.models.signal_event import SignalEvent
from freecoinalert_api.db.models.signal_event_invalidation import SignalEventInvalidation
from freecoinalert_api.db.models.signal_telegram_dispatch import SignalTelegramDispatch
from freecoinalert_api.db.repositories.notification_outbox import (
    create_telegram_preset_signal_notification,
)
from freecoinalert_api.db.repositories.signal_telegram_dispatches import (
    EligibleSignalSubscription,
    claim_signal_telegram_dispatches,
    fail_exhausted_signal_telegram_dispatches,
    get_signal_telegram_dispatch_for_update,
    list_eligible_signal_subscriptions,
    recover_stale_signal_telegram_dispatches,
)
from freecoinalert_api.db.session import get_async_session_factory

logger = logging.getLogger(__name__)
STALE_PROCESSING_AFTER = timedelta(minutes=5)
RETRY_BASE_SECONDS = 5
RETRY_MAX_SECONDS = 300
DESTINATION_UNAVAILABLE = "signal_telegram_destination_unavailable"


@dataclass(frozen=True, slots=True)
class DispatchPageOutcome:
    signal_event_id: uuid.UUID | None
    completed: bool
    created_count: int = 0
    skipped_count: int = 0
    status: str | None = None
    failure_category: str | None = None


class SignalTelegramDispatcher:
    def __init__(
        self,
        *,
        batch_size: int,
        claim_limit: int,
        poll_seconds: float,
        max_age_seconds: int,
        dispatcher_id: str,
    ) -> None:
        self._batch_size = batch_size
        self._claim_limit = claim_limit
        self._poll_seconds = poll_seconds
        self._max_age = timedelta(seconds=max_age_seconds)
        self._dispatcher_id = dispatcher_id
        self._stop_event = asyncio.Event()

    def request_shutdown(self) -> None:
        self._stop_event.set()

    async def run(self) -> int:
        logger.info("signal.telegram.dispatcher.starting")
        self._install_signal_handlers()
        while not self._stop_event.is_set():
            await self._claim_and_process()
            await self._sleep_until_next_poll()
        logger.info("signal.telegram.dispatcher.stopped")
        return 0

    async def _claim_and_process(self) -> None:
        current_time = datetime.now(UTC)
        session_factory = get_async_session_factory()
        try:
            async with session_factory() as session:
                async with session.begin():
                    recovered_count = await recover_stale_signal_telegram_dispatches(
                        session,
                        stale_before=current_time - STALE_PROCESSING_AFTER,
                        available_at=current_time,
                    )
                    exhausted_count = await fail_exhausted_signal_telegram_dispatches(
                        session,
                        failed_at=current_time,
                    )
                    dispatches = await claim_signal_telegram_dispatches(
                        session,
                        current_time=current_time,
                        dispatcher_id=self._dispatcher_id,
                        limit=self._claim_limit,
                    )
        except SQLAlchemyError:
            logger.error("signal.telegram.dispatch.failed failure_category=claim")
            return

        if recovered_count:
            logger.warning(
                "signal.telegram.dispatch.requeued stale_count=%s",
                recovered_count,
            )
        if exhausted_count:
            logger.error(
                "signal.telegram.dispatch.failed failure_category=attempts_exhausted "
                "dispatch_count=%s",
                exhausted_count,
            )

        for dispatch in dispatches:
            logger.info(
                "signal.telegram.dispatch.claimed signal_event_id=%s attempt_count=%s",
                dispatch.signal_event_id,
                dispatch.attempt_count,
            )
            await self._process_dispatch(dispatch.id)

    async def _process_dispatch(self, dispatch_id: uuid.UUID) -> None:
        while not self._stop_event.is_set():
            try:
                outcome = await self._process_page(dispatch_id)
            except SQLAlchemyError:
                logger.error(
                    "signal.telegram.dispatch.failed dispatch_id=%s "
                    "failure_category=database",
                    dispatch_id,
                )
                await self._schedule_retry(dispatch_id, failure_category="database")
                return
            except Exception:
                logger.error(
                    "signal.telegram.dispatch.failed dispatch_id=%s "
                    "failure_category=dispatcher_error",
                    dispatch_id,
                )
                await self._schedule_retry(dispatch_id, failure_category="dispatcher_error")
                return

            if outcome.signal_event_id is None:
                return
            if outcome.created_count or outcome.skipped_count:
                logger.info(
                    "signal.telegram.dispatch.page signal_event_id=%s "
                    "created_count=%s skipped_count=%s skip_category=%s",
                    outcome.signal_event_id,
                    outcome.created_count,
                    outcome.skipped_count,
                    outcome.failure_category,
                )
            if outcome.completed:
                logger.info(
                    "signal.telegram.dispatch.completed signal_event_id=%s status=%s",
                    outcome.signal_event_id,
                    outcome.status,
                )
                return

    async def _process_page(self, dispatch_id: uuid.UUID) -> DispatchPageOutcome:
        current_time = datetime.now(UTC)
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            async with session.begin():
                dispatch = await get_signal_telegram_dispatch_for_update(
                    session,
                    dispatch_id=dispatch_id,
                )
                if (
                    dispatch is None
                    or dispatch.status != "processing"
                    or dispatch.locked_by != self._dispatcher_id
                ):
                    return DispatchPageOutcome(signal_event_id=None, completed=True)

                signal_event = await session.get(SignalEvent, dispatch.signal_event_id)
                if signal_event is None:
                    self._mark_terminal(
                        dispatch,
                        status="failed",
                        current_time=current_time,
                        failure_code="signal_event_unavailable",
                    )
                    return DispatchPageOutcome(
                        signal_event_id=dispatch.signal_event_id,
                        completed=True,
                        status="failed",
                        failure_category="signal_event_unavailable",
                    )

                invalidated = await session.scalar(
                    select(SignalEventInvalidation.id).where(
                        SignalEventInvalidation.signal_event_id == signal_event.id
                    )
                )
                if invalidated is not None:
                    self._mark_terminal(
                        dispatch,
                        status="skipped",
                        current_time=current_time,
                        failure_code="signal_event_invalidated",
                    )
                    return DispatchPageOutcome(
                        signal_event_id=signal_event.id,
                        completed=True,
                        status="skipped",
                        failure_category="signal_event_invalidated",
                    )

                if signal_event.backfilled:
                    self._mark_terminal(
                        dispatch,
                        status="skipped",
                        current_time=current_time,
                        failure_code="historical_backfill_not_delivered",
                    )
                    return DispatchPageOutcome(
                        signal_event_id=signal_event.id,
                        completed=True,
                        status="skipped",
                        failure_category="historical_backfill_not_delivered",
                    )

                if current_time > signal_event.occurred_at + self._max_age:
                    self._mark_terminal(
                        dispatch,
                        status="skipped",
                        current_time=current_time,
                        failure_code="signal_telegram_dispatch_expired",
                    )
                    return DispatchPageOutcome(
                        signal_event_id=signal_event.id,
                        completed=True,
                        status="skipped",
                        failure_category="signal_telegram_dispatch_expired",
                    )

                subscriptions = await list_eligible_signal_subscriptions(
                    session,
                    signal_event=signal_event,
                    after_subscription_id=dispatch.last_subscription_id,
                    limit=self._batch_size,
                )
                if not subscriptions:
                    self._mark_terminal(
                        dispatch,
                        status="completed",
                        current_time=current_time,
                        failure_code=dispatch.failure_code,
                    )
                    return DispatchPageOutcome(
                        signal_event_id=signal_event.id,
                        completed=True,
                        status="completed",
                    )

                created_count = 0
                skipped_count = 0
                skip_category: str | None = None
                for subscription in subscriptions:
                    if not self._has_eligible_destination(
                        subscription,
                        occurred_at=signal_event.occurred_at,
                    ):
                        skipped_count += 1
                        skip_category = DESTINATION_UNAVAILABLE
                        continue

                    assert subscription.telegram_connection_id is not None
                    payload = _build_signal_payload(
                        signal_event,
                        subscription_id=subscription.subscription_id,
                    )
                    notification = await create_telegram_preset_signal_notification(
                        session,
                        user_id=subscription.user_id,
                        telegram_connection_id=subscription.telegram_connection_id,
                        signal_event_id=signal_event.id,
                        signal_subscription_id=subscription.subscription_id,
                        message_payload=payload,
                    )
                    if notification is not None:
                        created_count += 1

                dispatch.last_subscription_id = subscriptions[-1].subscription_id
                dispatch.notification_count += created_count
                dispatch.skipped_count += skipped_count
                if skip_category is not None and dispatch.failure_code is None:
                    dispatch.failure_code = skip_category
                dispatch.updated_at = current_time
                return DispatchPageOutcome(
                    signal_event_id=signal_event.id,
                    completed=False,
                    created_count=created_count,
                    skipped_count=skipped_count,
                    failure_category=skip_category,
                )

    async def _schedule_retry(self, dispatch_id: uuid.UUID, *, failure_category: str) -> None:
        current_time = datetime.now(UTC)
        session_factory = get_async_session_factory()
        try:
            async with session_factory() as session:
                async with session.begin():
                    dispatch = await get_signal_telegram_dispatch_for_update(
                        session,
                        dispatch_id=dispatch_id,
                    )
                    if (
                        dispatch is None
                        or dispatch.status != "processing"
                        or dispatch.locked_by != self._dispatcher_id
                    ):
                        return
                    if dispatch.attempt_count >= dispatch.max_attempts:
                        self._mark_terminal(
                            dispatch,
                            status="failed",
                            current_time=current_time,
                            failure_code="signal_telegram_fanout_attempts_exhausted",
                        )
                    else:
                        dispatch.status = "retry_wait"
                        dispatch.available_at = current_time + _retry_delay(
                            dispatch.attempt_count
                        )
                        dispatch.locked_at = None
                        dispatch.locked_by = None
                        dispatch.failure_code = (
                            f"signal_telegram_dispatch_{failure_category}"
                        )
                        dispatch.updated_at = current_time
        except SQLAlchemyError:
            logger.error(
                "signal.telegram.dispatch.failed dispatch_id=%s "
                "failure_category=retry_recording",
                dispatch_id,
            )

    @staticmethod
    def _has_eligible_destination(
        subscription: EligibleSignalSubscription,
        *,
        occurred_at: datetime,
    ) -> bool:
        connection_id = subscription.telegram_connection_id
        connection_status = subscription.telegram_connection_status
        connected_at = subscription.telegram_connected_at
        return (
            connection_id is not None
            and connection_status == "connected"
            and connected_at is not None
            and connected_at <= occurred_at
        )

    @staticmethod
    def _mark_terminal(
        dispatch: SignalTelegramDispatch,
        *,
        status: str,
        current_time: datetime,
        failure_code: str | None,
    ) -> None:
        dispatch.status = status
        dispatch.locked_at = None
        dispatch.locked_by = None
        dispatch.failure_code = failure_code
        dispatch.updated_at = current_time
        if status == "completed" or status == "skipped":
            dispatch.completed_at = current_time
        if status == "failed":
            dispatch.failed_at = current_time

    async def _sleep_until_next_poll(self) -> None:
        try:
            await asyncio.wait_for(
                self._stop_event.wait(),
                timeout=self._poll_seconds,
            )
        except TimeoutError:
            pass

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for signal_name in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(signal_name, self.request_shutdown)
            except NotImplementedError:
                signal.signal(signal_name, lambda *_: self.request_shutdown())


def _build_signal_payload(
    signal_event: SignalEvent,
    *,
    subscription_id: uuid.UUID,
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "messageType": "telegram_preset_signal",
        "signalEventId": str(signal_event.id),
        "signalSubscriptionId": str(subscription_id),
        "symbol": signal_event.symbol_snapshot,
        "baseAsset": signal_event.base_asset_snapshot,
        "quoteAsset": signal_event.quote_asset_snapshot,
        "presetCode": signal_event.preset_code_snapshot,
        "presetVersion": signal_event.preset_version_snapshot,
        "presetName": signal_event.preset_name_snapshot,
        "strategyType": signal_event.strategy_type_snapshot,
        "calculationVersion": signal_event.calculation_version_snapshot,
        "timeframe": signal_event.timeframe_snapshot,
        "direction": signal_event.direction_snapshot,
        "period": signal_event.period_snapshot,
        "threshold": _decimal_string(signal_event.threshold_snapshot),
        "priceInput": signal_event.price_input_snapshot,
        "candleRevision": signal_event.candle_revision,
        "candleOpenTime": _utc_timestamp(signal_event.candle_open_time),
        "candleCloseTime": _utc_timestamp(signal_event.candle_close_time),
        "previousLeftValue": _decimal_string(signal_event.previous_left_value),
        "previousRightValue": _decimal_string(signal_event.previous_right_value),
        "currentLeftValue": _decimal_string(signal_event.current_left_value),
        "currentRightValue": _decimal_string(signal_event.current_right_value),
        "candleClosePrice": _decimal_string(signal_event.candle_close_price),
        "occurredAt": _utc_timestamp(signal_event.occurred_at),
    }


def _decimal_string(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _retry_delay(attempt_count: int) -> timedelta:
    seconds = min(
        RETRY_BASE_SECONDS * (2 ** max(attempt_count - 1, 0)),
        RETRY_MAX_SECONDS,
    )
    return timedelta(seconds=seconds)


def create_dispatcher() -> SignalTelegramDispatcher:
    settings = get_settings()
    return SignalTelegramDispatcher(
        batch_size=settings.signal_telegram_fanout_batch_size,
        claim_limit=settings.signal_telegram_fanout_claim_limit,
        poll_seconds=settings.signal_telegram_fanout_poll_seconds,
        max_age_seconds=settings.signal_telegram_fanout_max_age_seconds,
        dispatcher_id=str(uuid.uuid4()),
    )


def main() -> None:
    dispatcher = create_dispatcher()
    raise SystemExit(asyncio.run(dispatcher.run()))


if __name__ == "__main__":
    main()
