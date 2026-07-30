import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from freecoinalert_api.alerts.relations import crosses_in_direction, relation_for
from freecoinalert_api.alerts.registry import ActiveAlertRegistry
from freecoinalert_api.db.repositories.alert_events import create_alert_event
from freecoinalert_api.db.repositories.notification_outbox import (
    create_telegram_price_alert_notification,
)
from freecoinalert_api.db.repositories.price_alerts import (
    get_price_alert_by_id_for_update,
    initialize_price_alert_relation,
    mark_price_alert_failed,
    mark_price_alert_triggered,
    update_price_alert_relation,
)
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.events import PriceEvent

logger = logging.getLogger(__name__)


class PriceAlertTrigger:
    def __init__(self, registry: ActiveAlertRegistry) -> None:
        self._registry = registry

    async def evaluate(self, *, alert_id: uuid.UUID, event: PriceEvent) -> None:
        async with get_async_session_factory()() as session:
            try:
                async with session.begin():
                    alert = await get_price_alert_by_id_for_update(session, alert_id=alert_id)
                    if alert is None or alert.status != "active":
                        self._registry.remove(
                            supported_market_id=event.supported_market_id,
                            alert_id=alert_id,
                        )
                        logger.info("alert.trigger.duplicate_suppressed category=terminal")
                        return
                    if (
                        alert.supported_market_id != event.supported_market_id
                        or alert.symbol_snapshot != event.symbol
                        or alert.exchange_snapshot != event.exchange
                        or alert.market_type_snapshot != event.market_type
                    ):
                        await mark_price_alert_failed(
                            session,
                            alert=alert,
                            failed_at=datetime.now(UTC),
                            reason="evaluation_invariant",
                        )
                        self._registry.remove(
                            supported_market_id=alert.supported_market_id,
                            alert_id=alert.id,
                        )
                        logger.error("alert.trigger.failed alert_id=%s category=evaluation_invariant", alert.id)
                        return
                    if (
                        alert.last_evaluated_provider_id is not None
                        and event.provider_event_id <= alert.last_evaluated_provider_id
                    ):
                        logger.info("alert.evaluation.skipped_old_event alert_id=%s", alert.id)
                        return

                    current = relation_for(price=event.price, target=alert.target_price)
                    if alert.last_relation is None:
                        await initialize_price_alert_relation(
                            session,
                            alert=alert,
                            relation=current,
                            observed_price=event.price,
                            provider_event_id=event.provider_event_id,
                            provider_event_time=event.provider_trade_time,
                        )
                        self._registry.apply(alert)
                        logger.info("alert.evaluation.initialized alert_id=%s", alert.id)
                        return

                    previous = alert.last_relation
                    if previous == current:
                        return
                    if not crosses_in_direction(
                        direction=alert.direction,
                        previous=previous,
                        current=current,
                    ):
                        await update_price_alert_relation(
                            session,
                            alert=alert,
                            relation=current,
                            observed_price=event.price,
                            provider_event_id=event.provider_event_id,
                            provider_event_time=event.provider_trade_time,
                        )
                        self._registry.apply(alert)
                        logger.info(
                            "alert.evaluation.relation_changed alert_id=%s previous=%s current=%s",
                            alert.id,
                            previous,
                            current,
                        )
                        return

                    alert_event = await create_alert_event(
                        session,
                        alert_id=alert.id,
                        user_id=alert.user_id,
                        telegram_connection_id=alert.telegram_connection_id,
                        exchange=alert.exchange_snapshot,
                        market_type=alert.market_type_snapshot,
                        symbol=alert.symbol_snapshot,
                        base_asset=alert.base_asset_snapshot,
                        quote_asset=alert.quote_asset_snapshot,
                        direction=alert.direction,
                        target_price=alert.target_price,
                        trigger_price=event.price,
                        provider_event_id=event.provider_event_id,
                        provider_event_time=event.provider_trade_time,
                        observed_at=event.received_at,
                        observed_after_reconnect=event.observed_after_reconnect,
                    )
                    await mark_price_alert_triggered(
                        session,
                        alert=alert,
                        triggered_at=event.received_at,
                        relation=current,
                        observed_price=event.price,
                        provider_event_id=event.provider_event_id,
                        provider_event_time=event.provider_trade_time,
                    )
                    notification = await create_telegram_price_alert_notification(
                        session,
                        user_id=alert.user_id,
                        telegram_connection_id=alert.telegram_connection_id,
                        alert_id=alert.id,
                        alert_event_id=alert_event.id,
                        symbol=alert.symbol_snapshot,
                        base_asset=alert.base_asset_snapshot,
                        quote_asset=alert.quote_asset_snapshot,
                        direction=alert.direction,
                        target_price=alert.target_price,
                        trigger_price=event.price,
                        triggered_at=event.received_at,
                    )
                    self._registry.remove(
                        supported_market_id=alert.supported_market_id,
                        alert_id=alert.id,
                    )
                    logger.info("alert.trigger.created alert_id=%s alert_event_id=%s", alert.id, alert_event.id)
                    logger.info("alert.notification.queued notification_id=%s", notification.id)
            except IntegrityError:
                await session.rollback()
                self._registry.remove(
                    supported_market_id=event.supported_market_id,
                    alert_id=alert_id,
                )
                logger.info("alert.trigger.duplicate_suppressed category=constraint")
            except (SQLAlchemyError, ValueError):
                await session.rollback()
                logger.exception("alert.trigger.failed category=transaction")
