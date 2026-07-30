import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from freecoinalert_api.db.models.price_alert import PriceAlert
from freecoinalert_api.db.repositories.price_alerts import (
    list_active_price_alerts,
    list_active_price_alerts_updated_since,
)
from freecoinalert_api.db.session import get_async_session_factory

logger = logging.getLogger(__name__)
REGISTRY_REFRESH_SECONDS = 2
REGISTRY_OVERLAP_SECONDS = 5
REGISTRY_REBUILD_SECONDS = 60


@dataclass(frozen=True, slots=True)
class ActiveAlert:
    id: uuid.UUID
    user_id: uuid.UUID
    supported_market_id: uuid.UUID
    telegram_connection_id: uuid.UUID
    direction: str
    target_price: Decimal
    status: str
    last_relation: str | None
    last_evaluated_provider_id: int | None

    @classmethod
    def from_model(cls, alert: PriceAlert) -> "ActiveAlert":
        return cls(
            id=alert.id,
            user_id=alert.user_id,
            supported_market_id=alert.supported_market_id,
            telegram_connection_id=alert.telegram_connection_id,
            direction=alert.direction,
            target_price=alert.target_price,
            status=alert.status,
            last_relation=alert.last_relation,
            last_evaluated_provider_id=alert.last_evaluated_provider_id,
        )


class ActiveAlertRegistry:
    def __init__(self) -> None:
        self._alerts_by_market: dict[uuid.UUID, dict[uuid.UUID, ActiveAlert]] = {}
        self._last_refresh_at = datetime.min.replace(tzinfo=UTC)
        self._last_rebuild_monotonic = 0.0

    def for_market(self, supported_market_id: uuid.UUID) -> tuple[ActiveAlert, ...]:
        return tuple(self._alerts_by_market.get(supported_market_id, {}).values())

    def grouped_alerts(self) -> tuple[tuple[uuid.UUID, tuple[ActiveAlert, ...]], ...]:
        return tuple(
            (market_id, tuple(alerts.values()))
            for market_id, alerts in self._alerts_by_market.items()
        )

    def apply(self, alert: PriceAlert) -> None:
        market_alerts = self._alerts_by_market.setdefault(alert.supported_market_id, {})
        if alert.status == "active":
            market_alerts[alert.id] = ActiveAlert.from_model(alert)
            return
        market_alerts.pop(alert.id, None)
        if not market_alerts:
            self._alerts_by_market.pop(alert.supported_market_id, None)

    def remove(self, *, supported_market_id: uuid.UUID, alert_id: uuid.UUID) -> None:
        market_alerts = self._alerts_by_market.get(supported_market_id)
        if market_alerts is None:
            return
        market_alerts.pop(alert_id, None)
        if not market_alerts:
            self._alerts_by_market.pop(supported_market_id, None)

    async def load_initial(self) -> None:
        await self._rebuild()

    async def refresh_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_rebuild_monotonic >= REGISTRY_REBUILD_SECONDS:
            await self._rebuild()
            return
        if datetime.now(UTC) - self._last_refresh_at < timedelta(seconds=REGISTRY_REFRESH_SECONDS):
            return
        await self._refresh_recent()

    async def _rebuild(self) -> None:
        try:
            async with get_async_session_factory()() as session:
                alerts = await list_active_price_alerts(session)
        except SQLAlchemyError:
            logger.exception("alert.registry.refresh_failed category=full_rebuild")
            return

        self._alerts_by_market = {}
        for alert in alerts:
            self.apply(alert)
        self._last_refresh_at = datetime.now(UTC)
        self._last_rebuild_monotonic = time.monotonic()
        logger.info("alert.registry.refreshed mode=full active_count=%s", len(alerts))

    async def _refresh_recent(self) -> None:
        since = self._last_refresh_at - timedelta(seconds=REGISTRY_OVERLAP_SECONDS)
        try:
            async with get_async_session_factory()() as session:
                alerts = await list_active_price_alerts_updated_since(session, updated_since=since)
        except SQLAlchemyError:
            logger.exception("alert.registry.refresh_failed category=incremental")
            return

        for alert in alerts:
            self.apply(alert)
        self._last_refresh_at = datetime.now(UTC)
        logger.info("alert.registry.refreshed mode=incremental changed_count=%s", len(alerts))
