import logging

from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.alerts.registry import ActiveAlertRegistry
from freecoinalert_api.alerts.trigger import PriceAlertTrigger
from freecoinalert_api.db.repositories.price_alerts import (
    get_price_alert_by_id_for_update,
    mark_price_alert_disabled,
)
from freecoinalert_api.db.repositories.supported_markets import list_product_markets
from freecoinalert_api.db.session import get_async_session_factory
from freecoinalert_api.market_data.catalog import is_market_ready, utc_now
from freecoinalert_api.market_data.events import PriceEvent

logger = logging.getLogger(__name__)


class PriceAlertEvaluator:
    def __init__(self, registry: ActiveAlertRegistry) -> None:
        self._registry = registry
        self._trigger = PriceAlertTrigger(registry)

    async def handle_price_event(self, event: PriceEvent) -> None:
        await self._registry.refresh_if_due()
        for alert in self._registry.for_market(event.supported_market_id):
            if (
                alert.last_evaluated_provider_id is not None
                and event.provider_event_id <= alert.last_evaluated_provider_id
            ):
                logger.info("alert.evaluation.skipped_old_event alert_id=%s", alert.id)
                continue
            await self._trigger.evaluate(alert_id=alert.id, event=event)

    async def reconcile_markets(self) -> None:
        try:
            async with get_async_session_factory()() as session:
                markets = {
                    market.id: market
                    for market in await list_product_markets(session)
                }
        except SQLAlchemyError:
            logger.exception("alert.registry.refresh_failed category=market_reconciliation")
            return

        for market_id, alerts in self._registry.grouped_alerts():
            market = markets.get(market_id)
            if market is not None and is_market_ready(
                market,
                current_time=utc_now(),
                max_age_seconds=24 * 60 * 60,
            ):
                continue
            for registered in alerts:
                try:
                    async with get_async_session_factory()() as session:
                        async with session.begin():
                            alert = await get_price_alert_by_id_for_update(
                                session,
                                alert_id=registered.id,
                            )
                            if alert is not None:
                                await mark_price_alert_disabled(
                                    session,
                                    alert=alert,
                                    disabled_at=utc_now(),
                                    reason="market_disabled",
                                )
                except SQLAlchemyError:
                    logger.exception("alert.registry.refresh_failed category=market_disable")
                    continue
                self._registry.remove(supported_market_id=market_id, alert_id=registered.id)
                logger.warning("alert.disabled.market alert_id=%s", registered.id)
