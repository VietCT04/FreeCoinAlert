import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.models.signal_preset import SignalPreset
from freecoinalert_api.db.models.signal_subscription import SignalSubscription
from freecoinalert_api.db.models.supported_market import SupportedMarket
from freecoinalert_api.db.repositories.signal_presets import (
    get_active_preset_by_code_version,
    get_preset_by_code_version,
    list_active_presets,
)
from freecoinalert_api.db.repositories.signal_subscriptions import (
    count_active_subscriptions_for_user,
    create_subscription,
    disable_subscription,
    get_subscription_combination_for_update,
    get_subscription_for_user,
    list_subscriptions_for_user,
    lock_user_subscription_creation,
    reactivate_subscription,
    update_telegram_delivery_preference,
)
from freecoinalert_api.db.repositories.supported_markets import get_alert_creation_ready_market
from freecoinalert_api.market_data.catalog import utc_now
from freecoinalert_api.schemas.signals import (
    SignalSubscriptionCreateRequest,
    SignalSubscriptionListEnvelope,
    SignalSubscriptionMarketResponse,
    SignalSubscriptionResponse,
    SignalTelegramDeliveryResponse,
)
from freecoinalert_api.signals.catalog import public_preset_response, subscription_preset_response
from freecoinalert_api.signals.errors import SignalError
from freecoinalert_api.telegram.errors import TelegramError
from freecoinalert_api.telegram.service import SafeTelegramConnection, telegram_connection_service

logger = logging.getLogger(__name__)
ACTIVE_SUBSCRIPTION_LIMIT = 20


@dataclass(frozen=True, slots=True)
class EnabledSubscription:
    subscription: SignalSubscription
    status_code: int
    result: str


@dataclass(frozen=True, slots=True)
class UpdatedTelegramDeliveryPreference:
    subscription: SignalSubscription
    telegram_connection: SafeTelegramConnection


class SignalSubscriptionService:
    async def list_presets(self, session: AsyncSession):
        try:
            presets = await list_active_presets(session)
            logger.info("signal.preset.catalog_loaded count=%s", len(presets))
            return [public_preset_response(preset) for preset in presets]
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def list_for_user(self, session: AsyncSession, *, user_id: uuid.UUID) -> SignalSubscriptionListEnvelope:
        try:
            telegram_connection = await telegram_connection_service.get_connection(
                session,
                user_id=user_id,
            )
            subscriptions = await list_subscriptions_for_user(session, user_id=user_id)
            return SignalSubscriptionListEnvelope(
                subscriptions=[
                    await self.response_for(
                        session,
                        subscription,
                        telegram_connection=telegram_connection,
                    )
                    for subscription in subscriptions
                ]
            )
        except TelegramError:
            await session.rollback()
            raise unavailable_error() from None
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def enable(self, session: AsyncSession, *, user_id: uuid.UUID, request: SignalSubscriptionCreateRequest, market_catalog_max_age_seconds: int) -> EnabledSubscription:
        try:
            await lock_user_subscription_creation(session, user_id=user_id)
            preset = await get_active_preset_by_code_version(
                session,
                code=request.preset_code,
                version=request.preset_version,
            )
            if preset is None:
                known_preset = await get_preset_by_code_version(
                    session,
                    code=request.preset_code,
                    version=request.preset_version,
                )
                if known_preset is None:
                    raise SignalError(
                        status_code=404,
                        code="SIGNAL_PRESET_NOT_FOUND",
                        message="The requested signal preset was not found.",
                    )
                raise SignalError(
                    status_code=409,
                    code="SIGNAL_PRESET_UNAVAILABLE",
                    message="The requested signal preset is unavailable.",
                )
            market = await get_alert_creation_ready_market(session, exchange=request.exchange, market_type=request.market_type, symbol=request.symbol, current_time=utc_now(), max_age_seconds=market_catalog_max_age_seconds)
            if market is None or market.base_asset is None or market.quote_asset is None:
                raise SignalError(status_code=422, code="SIGNAL_MARKET_UNAVAILABLE", message="This market is not available for signal subscriptions.")
            existing = await get_subscription_combination_for_update(session, user_id=user_id, supported_market_id=market.id, signal_preset_id=preset.id)
            if existing is not None and existing.status == "active":
                await session.commit()
                logger.info("signal.subscription.enable_replayed subscription_id=%s user_id=%s", existing.id, user_id)
                return EnabledSubscription(existing, 200, "replayed")
            if existing is None and await count_active_subscriptions_for_user(session, user_id=user_id) >= ACTIVE_SUBSCRIPTION_LIMIT:
                raise SignalError(status_code=409, code="SIGNAL_SUBSCRIPTION_LIMIT_REACHED", message="The active signal subscription limit has been reached.")
            now = datetime.now(timezone.utc)
            if existing is None:
                subscription = await create_subscription(session, user_id=user_id, supported_market_id=market.id, signal_preset_id=preset.id, activated_at=now)
                status_code = 201
                result = "created"
            else:
                await reactivate_subscription(
                    session,
                    subscription=existing,
                    activated_at=now,
                )
                subscription = existing
                status_code = 200
                result = "reactivated"
            await session.commit()
        except SignalError:
            await session.rollback()
            logger.info("signal.subscription.rejected user_id=%s", user_id)
            raise
        except (IntegrityError, SQLAlchemyError):
            await session.rollback()
            raise unavailable_error() from None
        logger.info("signal.subscription.%s subscription_id=%s user_id=%s", result, subscription.id, user_id)
        return EnabledSubscription(subscription, status_code, result)

    async def disable(self, session: AsyncSession, *, user_id: uuid.UUID, subscription_id: uuid.UUID) -> None:
        try:
            subscription = await get_subscription_for_user(session, user_id=user_id, subscription_id=subscription_id, for_update=True)
            if subscription is None:
                raise not_found_error()
            if subscription.status == "active":
                await disable_subscription(session, subscription=subscription, disabled_at=datetime.now(timezone.utc), reason="user_disabled")
            await session.commit()
        except SignalError:
            await session.rollback()
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None
        logger.info("signal.subscription.disabled subscription_id=%s user_id=%s", subscription_id, user_id)

    async def update_telegram_delivery(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        subscription_id: uuid.UUID,
        enabled: bool,
    ) -> UpdatedTelegramDeliveryPreference:
        try:
            subscription = await get_subscription_for_user(
                session,
                user_id=user_id,
                subscription_id=subscription_id,
                for_update=True,
            )
            if subscription is None:
                raise not_found_error()
            if enabled and subscription.status != "active":
                raise SignalError(
                    status_code=409,
                    code="SIGNAL_SUBSCRIPTION_INACTIVE",
                    message="Telegram delivery can only be enabled for an active subscription.",
                )

            telegram_connection = await self._telegram_connection(
                session,
                user_id=user_id,
            )
            if enabled and not subscription.telegram_delivery_enabled:
                self._require_ready_telegram_connection(telegram_connection)

            if subscription.telegram_delivery_enabled != enabled:
                now = datetime.now(timezone.utc)
                await update_telegram_delivery_preference(
                    session,
                    subscription=subscription,
                    enabled=enabled,
                    changed_at=now,
                )
                logger.info(
                    "signal.subscription.telegram_delivery_changed subscription_id=%s user_id=%s enabled=%s",
                    subscription_id,
                    user_id,
                    enabled,
                )
            await session.commit()
            return UpdatedTelegramDeliveryPreference(
                subscription=subscription,
                telegram_connection=telegram_connection,
            )
        except SignalError:
            await session.rollback()
            raise
        except TelegramError:
            await session.rollback()
            raise unavailable_error() from None
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def response_for(
        self,
        session: AsyncSession,
        subscription: SignalSubscription,
        *,
        telegram_connection: SafeTelegramConnection | None = None,
    ) -> SignalSubscriptionResponse:
        preset = await session.get(SignalPreset, subscription.signal_preset_id)
        market = await session.get(SupportedMarket, subscription.supported_market_id)
        if preset is None or market is None or market.base_asset is None or market.quote_asset is None:
            raise unavailable_error()
        if telegram_connection is None:
            telegram_connection = await self._telegram_connection(
                session,
                user_id=subscription.user_id,
            )
        return SignalSubscriptionResponse(
            id=subscription.id,
            status=subscription.status,
            status_reason=subscription.status_reason,
            market=SignalSubscriptionMarketResponse(exchange="binance", market_type="spot", symbol=market.symbol, base_asset=market.base_asset, quote_asset=market.quote_asset),
            preset=subscription_preset_response(preset),
            telegram_delivery=SignalTelegramDeliveryResponse(
                enabled=subscription.telegram_delivery_enabled,
                readiness=telegram_delivery_readiness(telegram_connection),
                status_reason=telegram_connection.status_reason,
                changed_at=subscription.telegram_delivery_changed_at,
            ),
            activated_at=subscription.activated_at,
            disabled_at=subscription.disabled_at,
        )

    async def _telegram_connection(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> SafeTelegramConnection:
        try:
            return await telegram_connection_service.get_connection(
                session,
                user_id=user_id,
            )
        except TelegramError:
            raise unavailable_error() from None

    @staticmethod
    def _require_ready_telegram_connection(
        telegram_connection: SafeTelegramConnection,
    ) -> None:
        if telegram_connection.status == "degraded":
            raise SignalError(
                status_code=409,
                code="SIGNAL_TELEGRAM_DEGRADED",
                message="Telegram is connected but currently degraded.",
            )
        if telegram_connection.status != "connected":
            raise SignalError(
                status_code=409,
                code="SIGNAL_TELEGRAM_NOT_CONNECTED",
                message="Connect Telegram before enabling signal delivery.",
            )


def telegram_delivery_readiness(
    telegram_connection: SafeTelegramConnection,
) -> Literal["ready", "linking", "not_connected", "degraded"]:
    if telegram_connection.status == "connected":
        return "ready"
    if telegram_connection.status == "degraded":
        return "degraded"
    if telegram_connection.status == "linking":
        return "linking"
    return "not_connected"


def not_found_error() -> SignalError:
    return SignalError(status_code=404, code="SIGNAL_SUBSCRIPTION_NOT_FOUND", message="The signal subscription was not found.")


def unavailable_error() -> SignalError:
    return SignalError(status_code=503, code="SIGNAL_SUBSCRIPTION_UNAVAILABLE", message="Signal subscriptions are temporarily unavailable.")


signal_subscription_service = SignalSubscriptionService()
