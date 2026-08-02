import base64
import binascii
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from freecoinalert_api.db.repositories.signal_feed_stream_events import (
    SignalFeedHistoryRecord,
    SignalFeedStreamRecord,
    get_active_replay_record,
    get_latest_stream_sequence,
    get_oldest_stream_sequence,
    get_stream_record,
    list_active_replay_records,
    list_visible_history_records,
)
from freecoinalert_api.schemas.signals import (
    SignalFeedCandleResponse,
    SignalFeedComparisonResponse,
    SignalFeedEnvelope,
    SignalFeedEventResponse,
    SignalFeedMarketResponse,
    SignalFeedPresetResponse,
    SignalParametersResponse,
)
from freecoinalert_api.signals.errors import SignalError

logger = logging.getLogger(__name__)
MAX_STREAM_SEQUENCE = 9_223_372_036_854_775_807
INVALIDATION_MESSAGES = {
    "candle_corrected": "Corrected market data changed this historical signal.",
    "calculation_invariant": "This historical signal was invalidated after a calculation review.",
    "preset_disabled": "This historical signal was invalidated because the preset was not valid for evaluation.",
}


@dataclass(frozen=True, slots=True)
class SignalFeedReplayPlan:
    high_water_sequence: int
    records: list[SignalFeedStreamRecord]
    reset_required: bool


class SignalFeedService:
    async def list_history(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int,
        cursor: str | None,
        status: Literal["current", "invalidated", "all"],
    ) -> SignalFeedEnvelope:
        started_at = time.monotonic()
        parsed_cursor = decode_history_cursor(cursor) if cursor is not None else None
        try:
            records = await list_visible_history_records(
                session,
                user_id=user_id,
                limit=limit + 1,
                cursor=parsed_cursor,
                status=status,
            )
            stream_cursor = await get_latest_stream_sequence(session)
        except SQLAlchemyError:
            await session.rollback()
            raise feed_unavailable_error() from None

        has_next_page = len(records) > limit
        visible_records = list(records[:limit])
        next_cursor = None
        if has_next_page and visible_records:
            last_event = visible_records[-1].signal_event
            next_cursor = encode_history_cursor(last_event.occurred_at, last_event.id)
        logger.info(
            "signal.feed.history_read user_id=%s count=%s has_next_page=%s stream_cursor=%s",
            user_id,
            len(visible_records),
            has_next_page,
            stream_cursor,
        )
        logger.info(
            "signal.feed.history_latency duration_ms=%s user_id=%s",
            int((time.monotonic() - started_at) * 1000),
            user_id,
        )
        return SignalFeedEnvelope(
            events=[signal_feed_event_response(record) for record in visible_records],
            next_cursor=next_cursor,
            stream_cursor=str(stream_cursor),
        )

    async def prepare_replay(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        after_sequence: int,
    ) -> SignalFeedReplayPlan:
        try:
            oldest_sequence = await get_oldest_stream_sequence(session)
            high_water_sequence = await get_latest_stream_sequence(session)
            if oldest_sequence is not None and after_sequence < oldest_sequence - 1:
                logger.info(
                    "signal.feed.reset_required user_id=%s reason=history_required",
                    user_id,
                )
                return SignalFeedReplayPlan(
                    high_water_sequence=high_water_sequence,
                    records=[],
                    reset_required=True,
                )
            records = list(
                await list_active_replay_records(
                    session,
                    user_id=user_id,
                    after_sequence=after_sequence,
                    through_sequence=high_water_sequence,
                    limit=101,
                )
            )
        except SQLAlchemyError:
            await session.rollback()
            raise feed_unavailable_error() from None

        reset_required = len(records) > 100
        if reset_required:
            logger.info(
                "signal.feed.reset_required user_id=%s reason=replay_limit",
                user_id,
            )
        return SignalFeedReplayPlan(
            high_water_sequence=high_water_sequence,
            records=records[:100],
            reset_required=reset_required,
        )

    async def stream_record_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        sequence: int,
    ) -> SignalFeedStreamRecord | None:
        try:
            return await get_active_replay_record(
                session,
                user_id=user_id,
                sequence=sequence,
            )
        except SQLAlchemyError:
            await session.rollback()
            raise feed_unavailable_error() from None

    async def stream_record(
        self,
        session: AsyncSession,
        *,
        sequence: int,
    ) -> SignalFeedStreamRecord | None:
        try:
            return await get_stream_record(session, sequence=sequence)
        except SQLAlchemyError:
            await session.rollback()
            raise feed_unavailable_error() from None


def signal_feed_event_response(
    record: SignalFeedStreamRecord | SignalFeedHistoryRecord,
) -> SignalFeedEventResponse:
    event = record.signal_event
    invalidation = record.invalidation
    invalidation_reason = None if invalidation is None else safe_invalidation_reason(invalidation.reason)
    preset_parameters = SignalParametersResponse(
        period=event.period_snapshot,
        threshold=canonical_decimal_string(event.threshold_snapshot),
        price_input="close",
    )
    if event.strategy_type_snapshot == "price_sma_cross":
        left_label = "price"
        right_label = "sma_200"
    else:
        left_label = f"rsi_{event.period_snapshot}"
        right_label = "threshold"
    return SignalFeedEventResponse(
        id=event.id,
        status="invalidated" if invalidation is not None else "current",
        invalidation_reason=invalidation_reason,
        market=SignalFeedMarketResponse(
            exchange=event.exchange_snapshot,
            market_type=event.market_type_snapshot,
            symbol=event.symbol_snapshot,
            base_asset=event.base_asset_snapshot,
            quote_asset=event.quote_asset_snapshot,
        ),
        preset=SignalFeedPresetResponse(
            code=event.preset_code_snapshot,
            version=event.preset_version_snapshot,
            name=event.preset_name_snapshot,
            strategy_type=event.strategy_type_snapshot,
            timeframe=event.timeframe_snapshot,
            direction=event.direction_snapshot,
            parameters=preset_parameters,
        ),
        comparison=SignalFeedComparisonResponse(
            left_label=left_label,
            right_label=right_label,
            previous_left=canonical_decimal_string(event.previous_left_value),
            previous_right=canonical_decimal_string(event.previous_right_value),
            current_left=canonical_decimal_string(event.current_left_value),
            current_right=canonical_decimal_string(event.current_right_value),
        ),
        candle=SignalFeedCandleResponse(
            revision=event.candle_revision,
            close_price=canonical_decimal_string(event.candle_close_price),
            open_time=event.candle_open_time,
            close_time=event.candle_close_time,
        ),
        backfilled=event.backfilled,
        occurred_at=event.occurred_at,
        recorded_at=event.created_at,
    )


def stream_sse_event(record: SignalFeedStreamRecord, *, delivery_mode: Literal["live", "replay"]) -> str:
    if record.stream_event.kind == "signal_invalidated":
        payload = {
            "eventId": str(record.signal_event.id),
            "reason": safe_invalidation_reason(
                record.invalidation.reason if record.invalidation is not None else "calculation_invariant"
            ),
            "deliveryMode": delivery_mode,
        }
        return sse_message(
            sequence=record.stream_event.sequence,
            event_name="signal_invalidated",
            payload=payload,
        )
    payload = signal_feed_event_response(record).model_dump(mode="json", by_alias=True)
    payload["deliveryMode"] = delivery_mode
    return sse_message(
        sequence=record.stream_event.sequence,
        event_name="signal",
        payload=payload,
    )


def sse_message(*, sequence: int | None = None, event_name: str, payload: dict[str, object]) -> str:
    lines: list[str] = []
    if sequence is not None:
        lines.append(f"id: {sequence}")
    lines.append(f"event: {event_name}")
    lines.append(f"data: {json.dumps(payload, separators=(',', ':'))}")
    return "\n".join(lines) + "\n\n"


def reset_sse_message() -> str:
    return sse_message(
        event_name="reset",
        payload={"reason": "history_required"},
    )


def auth_expired_sse_message() -> str:
    return sse_message(event_name="auth_expired", payload={})


def encode_history_cursor(occurred_at: datetime, event_id: uuid.UUID) -> str:
    payload = f"{occurred_at.astimezone(UTC).isoformat()}|{event_id}"
    return base64.urlsafe_b64encode(payload.encode("ascii")).decode("ascii").rstrip("=")


def decode_history_cursor(value: str) -> tuple[datetime, uuid.UUID]:
    if not value or len(value) > 256:
        raise feed_cursor_invalid_error()
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        occurred_at_value, event_id_value = decoded.split("|", maxsplit=1)
        occurred_at = datetime.fromisoformat(occurred_at_value)
        event_id = uuid.UUID(event_id_value)
    except (ValueError, UnicodeError, binascii.Error):
        raise feed_cursor_invalid_error() from None
    if occurred_at.tzinfo is None:
        raise feed_cursor_invalid_error()
    return occurred_at.astimezone(UTC), event_id


def parse_feed_limit(value: str | None) -> int:
    if value is None:
        return 50
    try:
        limit = int(value)
    except ValueError:
        raise feed_request_invalid_error() from None
    if limit < 1 or limit > 100:
        raise feed_request_invalid_error()
    return limit


def parse_feed_status(value: str | None) -> Literal["current", "invalidated", "all"]:
    if value is None:
        return "current"
    if value not in {"current", "invalidated", "all"}:
        raise feed_request_invalid_error()
    return value  # type: ignore[return-value]


def parse_stream_cursor(value: str | None) -> int | None:
    if value is None:
        return None
    if not value or not value.isascii() or not value.isdecimal():
        raise stream_cursor_invalid_error()
    sequence = int(value)
    if sequence > MAX_STREAM_SEQUENCE:
        raise stream_cursor_invalid_error()
    return sequence


def resolve_stream_cursor(*, last_event_id: str | None, after: str | None) -> int:
    last_sequence = parse_stream_cursor(last_event_id)
    after_sequence = parse_stream_cursor(after)
    if last_sequence is None and after_sequence is None:
        return 0
    return max(last_sequence or 0, after_sequence or 0)


def canonical_decimal_string(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def safe_invalidation_reason(reason: str) -> str:
    return INVALIDATION_MESSAGES.get(reason, INVALIDATION_MESSAGES["calculation_invariant"])


def feed_cursor_invalid_error() -> SignalError:
    return SignalError(
        status_code=422,
        code="SIGNAL_FEED_CURSOR_INVALID",
        message="The signal feed cursor is invalid.",
    )


def stream_cursor_invalid_error() -> SignalError:
    return SignalError(
        status_code=422,
        code="SIGNAL_FEED_STREAM_CURSOR_INVALID",
        message="The signal feed stream cursor is invalid.",
    )


def feed_request_invalid_error() -> SignalError:
    return SignalError(
        status_code=422,
        code="SIGNAL_FEED_REQUEST_INVALID",
        message="The signal feed request is invalid.",
    )


def feed_unavailable_error() -> SignalError:
    return SignalError(
        status_code=503,
        code="SIGNAL_FEED_UNAVAILABLE",
        message="The signal feed is temporarily unavailable.",
    )


signal_feed_service = SignalFeedService()
