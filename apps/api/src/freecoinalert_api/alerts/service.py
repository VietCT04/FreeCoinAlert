import base64
import binascii
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.alerts.errors import AlertError
from freecoinalert_api.db.models.alert_event import AlertEvent
from freecoinalert_api.db.models.price_alert import PriceAlert
from freecoinalert_api.db.repositories.alert_events import get_alert_event_for_alert
from freecoinalert_api.db.repositories.market_symbol_states import get_market_symbol_state
from freecoinalert_api.db.repositories.notification_outbox import (
    get_notification_by_user_and_idempotency_key,
)
from freecoinalert_api.db.repositories.price_alerts import (
    count_active_price_alerts_for_user,
    create_price_alert,
    get_price_alert_by_user_and_idempotency_key,
    get_price_alert_for_user,
    get_price_alert_for_user_for_update,
    list_price_alerts_page_for_user,
    lock_user_price_alert_creation,
    mark_price_alert_deleted,
)
from freecoinalert_api.db.repositories.supported_markets import get_alert_creation_ready_market
from freecoinalert_api.db.repositories.telegram import get_telegram_connection_by_user_id
from freecoinalert_api.market_data.catalog import utc_now
from freecoinalert_api.schemas.price_alerts import (
    PriceAlertCreateRequest,
    PriceAlertDeliveryResponse,
    PriceAlertListEnvelope,
    PriceAlertMarketDataResponse,
    PriceAlertMarketResponse,
    PriceAlertResponse,
    PriceAlertTriggerResponse,
)

logger = logging.getLogger(__name__)
PLAIN_DECIMAL_PATTERN = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
ACTIVE_ALERT_LIMIT = 20


@dataclass(frozen=True, slots=True)
class CreatedPriceAlert:
    alert: PriceAlert
    replayed: bool


class PriceAlertService:
    async def find_replay(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        idempotency_key: str,
        request: PriceAlertCreateRequest,
    ) -> PriceAlert | None:
        try:
            target_price = parse_target_price(request.target_price)
            existing = await get_price_alert_by_user_and_idempotency_key(
                session,
                user_id=user_id,
                creation_idempotency_key=idempotency_key,
            )
            if existing is not None:
                self._require_matching_replay(existing, request, target_price)
                logger.info(
                    "alert.price.create_replayed alert_id=%s user_id=%s",
                    existing.id,
                    user_id,
                )
            return existing
        except AlertError:
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        idempotency_key: str,
        request: PriceAlertCreateRequest,
        market_catalog_max_age_seconds: int,
    ) -> CreatedPriceAlert:
        target_price = parse_target_price(request.target_price)
        existing = await get_price_alert_by_user_and_idempotency_key(
            session,
            user_id=user_id,
            creation_idempotency_key=idempotency_key,
        )
        if existing is not None:
            self._require_matching_replay(existing, request, target_price)
            logger.info(
                "alert.price.create_replayed alert_id=%s user_id=%s",
                existing.id,
                user_id,
            )
            return CreatedPriceAlert(alert=existing, replayed=True)

        try:
            await lock_user_price_alert_creation(session, user_id=user_id)
            existing = await get_price_alert_by_user_and_idempotency_key(
                session,
                user_id=user_id,
                creation_idempotency_key=idempotency_key,
            )
            if existing is not None:
                self._require_matching_replay(existing, request, target_price)
                logger.info(
                    "alert.price.create_replayed alert_id=%s user_id=%s",
                    existing.id,
                    user_id,
                )
                return CreatedPriceAlert(alert=existing, replayed=True)

            active_count = await count_active_price_alerts_for_user(
                session,
                user_id=user_id,
            )
            if active_count >= ACTIVE_ALERT_LIMIT:
                raise AlertError(
                    status_code=409,
                    code="ALERT_ACTIVE_LIMIT_REACHED",
                    message="The active alert limit has been reached.",
                )

            market = await get_alert_creation_ready_market(
                session,
                exchange=request.exchange,
                market_type=request.market_type,
                symbol=request.symbol,
                current_time=utc_now(),
                max_age_seconds=market_catalog_max_age_seconds,
            )
            if market is None or market.base_asset is None or market.quote_asset is None:
                raise AlertError(
                    status_code=422,
                    code="ALERT_MARKET_UNAVAILABLE",
                    message="This market is not available for new alerts.",
                )

            validate_target_against_market(target_price, market)
            connection = await get_telegram_connection_by_user_id(
                session,
                user_id=user_id,
                for_update=True,
            )
            if connection is None or connection.status == "disconnected":
                raise AlertError(
                    status_code=409,
                    code="ALERT_TELEGRAM_NOT_CONNECTED",
                    message="Connect Telegram before creating an alert.",
                )
            if connection.status == "degraded":
                raise AlertError(
                    status_code=409,
                    code="ALERT_TELEGRAM_DEGRADED",
                    message="Reconnect Telegram before creating an alert.",
                )

            alert = await create_price_alert(
                session,
                user_id=user_id,
                supported_market_id=market.id,
                telegram_connection_id=connection.id,
                creation_idempotency_key=idempotency_key,
                direction=request.direction,
                target_price=target_price,
                exchange_snapshot=market.exchange,
                market_type_snapshot=market.market_type,
                symbol_snapshot=market.symbol,
                base_asset_snapshot=market.base_asset,
                quote_asset_snapshot=market.quote_asset,
                price_tick_snapshot=market.price_tick,
            )
            await session.commit()
        except AlertError:
            await session.rollback()
            logger.info("alert.price.creation_rejected user_id=%s", user_id)
            raise
        except IntegrityError:
            await session.rollback()
            existing = await get_price_alert_by_user_and_idempotency_key(
                session,
                user_id=user_id,
                creation_idempotency_key=idempotency_key,
            )
            if existing is not None:
                self._require_matching_replay(existing, request, target_price)
                return CreatedPriceAlert(alert=existing, replayed=True)
            raise unavailable_error() from None
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

        logger.info(
            "alert.price.created alert_id=%s user_id=%s symbol=%s direction=%s",
            alert.id,
            user_id,
            alert.symbol_snapshot,
            alert.direction,
        )
        return CreatedPriceAlert(alert=alert, replayed=False)

    async def get_response(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        alert_id: uuid.UUID,
    ) -> PriceAlertResponse:
        try:
            alert = await get_price_alert_for_user(
                session,
                alert_id=alert_id,
                user_id=user_id,
            )
            if alert is None:
                raise not_found_error()
            return await self.response_for(session, alert)
        except AlertError:
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def list_response(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit_value: str | None,
        cursor_value: str | None,
        status_value: str | None,
    ) -> PriceAlertListEnvelope:
        limit = parse_limit(limit_value)
        status = parse_status(status_value)
        cursor_created_at, cursor_id = decode_cursor(cursor_value)
        try:
            alerts = await list_price_alerts_page_for_user(
                session,
                user_id=user_id,
                limit=limit + 1,
                status=status,
                cursor_created_at=cursor_created_at,
                cursor_id=cursor_id,
            )
            page_alerts = alerts[:limit]
            next_cursor = None
            if len(alerts) > limit:
                last_alert = page_alerts[-1]
                next_cursor = encode_cursor(last_alert.created_at, last_alert.id)
            return PriceAlertListEnvelope(
                alerts=[await self.response_for(session, alert) for alert in page_alerts],
                next_cursor=next_cursor,
            )
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    async def delete(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        alert_id: uuid.UUID,
    ) -> None:
        try:
            alert = await get_price_alert_for_user_for_update(
                session,
                alert_id=alert_id,
                user_id=user_id,
            )
            if alert is None:
                raise not_found_error()
            if alert.status == "deleted":
                await session.commit()
                return
            if alert.status in {"triggered", "failed"}:
                raise AlertError(
                    status_code=409,
                    code="ALERT_NOT_DELETABLE",
                    message="This alert cannot be deleted.",
                )
            if not await mark_price_alert_deleted(
                session,
                alert=alert,
                deleted_at=datetime.now(timezone.utc),
            ):
                raise AlertError(
                    status_code=409,
                    code="ALERT_NOT_DELETABLE",
                    message="This alert cannot be deleted.",
                )
            await session.commit()
        except AlertError:
            await session.rollback()
            logger.info("alert.price.delete_rejected alert_id=%s user_id=%s", alert_id, user_id)
            raise
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

        logger.info("alert.price.deleted alert_id=%s user_id=%s", alert_id, user_id)

    async def response_for(self, session: AsyncSession, alert: PriceAlert) -> PriceAlertResponse:
        try:
            event = await get_alert_event_for_alert(session, alert_id=alert.id)
            trigger = trigger_response(event)
            notification = await get_notification_by_user_and_idempotency_key(
                session,
                user_id=alert.user_id,
                idempotency_key=f"price-alert:{alert.id}",
            )
            market_state = await get_market_symbol_state(
                session,
                supported_market_id=alert.supported_market_id,
            )
            return PriceAlertResponse(
                id=alert.id,
                type="price_cross",
                market=PriceAlertMarketResponse(
                    exchange=alert.exchange_snapshot,
                    market_type=alert.market_type_snapshot,
                    symbol=alert.symbol_snapshot,
                    base_asset=alert.base_asset_snapshot,
                    quote_asset=alert.quote_asset_snapshot,
                ),
                direction=alert.direction,
                target_price=canonical_decimal_string(alert.target_price),
                status=alert.status,
                status_reason=alert.status_reason,
                evaluation_ready=alert.last_relation is not None,
                last_observed_price=(
                    canonical_decimal_string(alert.last_evaluated_price)
                    if alert.last_evaluated_price is not None
                    else None
                ),
                created_at=alert.created_at,
                trigger=trigger,
                delivery=delivery_response(notification),
                market_data=market_data_response(market_state),
            )
        except SQLAlchemyError:
            await session.rollback()
            raise unavailable_error() from None

    @staticmethod
    def _require_matching_replay(
        alert: PriceAlert,
        request: PriceAlertCreateRequest,
        target_price: Decimal,
    ) -> None:
        if (
            alert.exchange_snapshot != request.exchange
            or alert.market_type_snapshot != request.market_type
            or alert.symbol_snapshot != request.symbol
            or alert.direction != request.direction
            or alert.target_price != target_price
        ):
            raise AlertError(
                status_code=409,
                code="ALERT_IDEMPOTENCY_CONFLICT",
                message="The Idempotency-Key was already used for a different alert.",
            )


def parse_target_price(value: str) -> Decimal:
    if len(value) > 64 or PLAIN_DECIMAL_PATTERN.fullmatch(value) is None:
        raise target_invalid_error()
    try:
        target_price = Decimal(value)
    except InvalidOperation:
        raise target_invalid_error() from None
    if (
        not target_price.is_finite()
        or target_price <= 0
        or -target_price.as_tuple().exponent > 18
    ):
        raise target_invalid_error()
    return target_price


def validate_target_against_market(target_price: Decimal, market: object) -> None:
    minimum = getattr(market, "min_price")
    maximum = getattr(market, "max_price")
    tick = getattr(market, "price_tick")
    if tick is None or tick <= 0:
        raise target_invalid_error()
    if minimum is not None and minimum > 0 and target_price < minimum:
        raise target_invalid_error()
    if maximum is not None and maximum > 0 and target_price > maximum:
        raise target_invalid_error()
    if target_price % tick != 0:
        raise target_invalid_error()


def validate_idempotency_key(value: str | None) -> str:
    if value is None or len(value) > 128:
        raise AlertError(
            status_code=422,
            code="ALERT_IDEMPOTENCY_KEY_INVALID",
            message="The Idempotency-Key header must be a UUID.",
        )
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise AlertError(
            status_code=422,
            code="ALERT_IDEMPOTENCY_KEY_INVALID",
            message="The Idempotency-Key header must be a UUID.",
        ) from None


def parse_limit(value: str | None) -> int:
    if value is None:
        return 20
    try:
        limit = int(value)
    except ValueError:
        raise request_invalid_error() from None
    if limit < 1 or limit > 50 or str(limit) != value:
        raise request_invalid_error()
    return limit


def parse_status(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in {"active", "triggered", "disabled", "failed"}:
        raise request_invalid_error()
    return value


def encode_cursor(created_at: datetime, alert_id: uuid.UUID) -> str:
    payload = json.dumps(
        {"createdAt": created_at.isoformat(), "id": str(alert_id)},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(value: str | None) -> tuple[datetime | None, uuid.UUID | None]:
    if value is None:
        return None, None
    try:
        padding = "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(value + padding).decode("utf-8"))
        created_at = datetime.fromisoformat(payload["createdAt"])
        alert_id = uuid.UUID(payload["id"])
        if created_at.tzinfo is None:
            raise ValueError
        return created_at, alert_id
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ):
        raise cursor_invalid_error() from None


def canonical_decimal_string(value: Decimal) -> str:
    return format(value, "f")


def trigger_response(event: AlertEvent | None) -> PriceAlertTriggerResponse | None:
    if event is None:
        return None
    return PriceAlertTriggerResponse(
        price=canonical_decimal_string(event.trigger_price),
        occurred_at=event.observed_at,
    )


def delivery_response(notification: object | None) -> PriceAlertDeliveryResponse:
    if notification is None:
        return PriceAlertDeliveryResponse(status="not_queued")
    status = getattr(notification, "status")
    if status == "pending":
        mapped = "queued"
    elif status == "processing":
        mapped = "sending"
    elif status == "retry_wait":
        mapped = "retrying"
    elif status == "sent":
        mapped = "sent"
    elif getattr(notification, "failure_code") == "telegram_delivery_outcome_unknown":
        mapped = "outcome_unknown"
    else:
        mapped = "failed"
    return PriceAlertDeliveryResponse(
        status=mapped,
        sent_at=getattr(notification, "sent_at"),
        failure_code=(None if mapped != "failed" else getattr(notification, "failure_code")),
    )


def market_data_response(state: object | None) -> PriceAlertMarketDataResponse:
    raw_status = None if state is None else getattr(state, "status")
    status = raw_status if raw_status in {"live", "stale", "disconnected"} else "unavailable"
    return PriceAlertMarketDataResponse(
        status=status,
        last_observed_at=(None if state is None else getattr(state, "last_received_at")),
    )


def request_invalid_error() -> AlertError:
    return AlertError(
        status_code=422,
        code="ALERT_REQUEST_INVALID",
        message="The alert request is invalid.",
    )


def target_invalid_error() -> AlertError:
    return AlertError(
        status_code=422,
        code="ALERT_TARGET_INVALID",
        message="The target price is invalid for this market.",
    )


def cursor_invalid_error() -> AlertError:
    return AlertError(
        status_code=422,
        code="ALERT_CURSOR_INVALID",
        message="The alert cursor is invalid.",
    )


def not_found_error() -> AlertError:
    return AlertError(
        status_code=404,
        code="ALERT_NOT_FOUND",
        message="The alert was not found.",
    )


def unavailable_error() -> AlertError:
    return AlertError(
        status_code=503,
        code="ALERT_UNAVAILABLE",
        message="Alert management is temporarily unavailable.",
    )


price_alert_service = PriceAlertService()
