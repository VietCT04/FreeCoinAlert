"""Strict internal payloads for provider-facing notification jobs."""

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

DecimalString = StrictStr
SignalStrategy = Literal["price_sma_cross", "rsi_threshold_cross"]
SignalCalculationVersion = Literal["sma_close_v1", "rsi_wilder_close_v1"]
SignalTimeframe = Literal["1h", "4h"]
SignalDirection = Literal["cross_above", "cross_below"]

_DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?\Z")
_SNAPSHOT_STRING_FIELDS = (
    "symbol",
    "base_asset",
    "quote_asset",
    "preset_code",
    "preset_name",
)
_DECIMAL_FIELDS = (
    "previous_left_value",
    "previous_right_value",
    "current_left_value",
    "current_right_value",
    "candle_close_price",
)
_TIMESTAMP_FIELDS = (
    "candle_open_time",
    "candle_close_time",
    "occurred_at",
)


class NotificationPayloadError(ValueError):
    """Raised when a provider-facing notification payload is unsafe to send."""


class PresetSignalPayload(BaseModel):
    """Immutable schema-versioned payload consumed by the notification worker."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: StrictInt = Field(alias="schemaVersion")
    message_type: Literal["telegram_preset_signal"] = Field(alias="messageType")
    signal_event_id: UUID = Field(alias="signalEventId")
    signal_subscription_id: UUID = Field(alias="signalSubscriptionId")
    symbol: StrictStr
    base_asset: StrictStr = Field(alias="baseAsset")
    quote_asset: StrictStr = Field(alias="quoteAsset")
    preset_code: StrictStr = Field(alias="presetCode")
    preset_version: StrictInt = Field(alias="presetVersion")
    preset_name: StrictStr = Field(alias="presetName")
    strategy_type: SignalStrategy = Field(alias="strategyType")
    calculation_version: SignalCalculationVersion = Field(alias="calculationVersion")
    timeframe: SignalTimeframe
    direction: SignalDirection
    period: StrictInt
    threshold: DecimalString | None
    price_input: Literal["close"] = Field(alias="priceInput")
    candle_revision: StrictInt = Field(alias="candleRevision")
    candle_open_time: datetime = Field(alias="candleOpenTime")
    candle_close_time: datetime = Field(alias="candleCloseTime")
    previous_left_value: DecimalString = Field(alias="previousLeftValue")
    previous_right_value: DecimalString = Field(alias="previousRightValue")
    current_left_value: DecimalString = Field(alias="currentLeftValue")
    current_right_value: DecimalString = Field(alias="currentRightValue")
    candle_close_price: DecimalString = Field(alias="candleClosePrice")
    occurred_at: datetime = Field(alias="occurredAt")

    @field_validator("signal_event_id", "signal_subscription_id", mode="before")
    @classmethod
    def validate_uuid(cls, value: object) -> UUID:
        if not isinstance(value, str):
            raise ValueError("UUID snapshots must be strings.")

        try:
            return UUID(value)
        except (ValueError, AttributeError):
            raise ValueError("UUID snapshot is invalid.") from None

    @field_validator(*_TIMESTAMP_FIELDS, mode="before")
    @classmethod
    def validate_utc_timestamp(cls, value: object) -> datetime:
        if not isinstance(value, str):
            raise ValueError("Timestamp snapshots must be strings.")

        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            raise ValueError("Timestamp snapshot is invalid.") from None

        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError("Timestamp snapshot must be UTC.")

        return parsed.astimezone(UTC)

    @field_validator("threshold", mode="before")
    @classmethod
    def validate_optional_decimal(cls, value: object) -> str | None:
        if value is None:
            return None
        return _validate_decimal_string(value)

    @field_validator(*_DECIMAL_FIELDS, mode="before")
    @classmethod
    def validate_decimal(cls, value: object) -> str:
        return _validate_decimal_string(value)

    @field_validator(*_SNAPSHOT_STRING_FIELDS)
    @classmethod
    def validate_snapshot_string(cls, value: str) -> str:
        if not value or value != value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError("Snapshot text is invalid.")
        return value

    @model_validator(mode="after")
    def validate_schema_and_strategy(self) -> "PresetSignalPayload":
        if self.schema_version != 1:
            raise ValueError("Unsupported notification payload schema.")
        if self.preset_version <= 0 or self.candle_revision <= 0:
            raise ValueError("Snapshot versions must be positive.")
        if self.candle_close_time <= self.candle_open_time:
            raise ValueError("Candle timestamps are invalid.")

        if self.strategy_type == "price_sma_cross":
            if (
                self.calculation_version != "sma_close_v1"
                or self.period != 200
                or self.threshold is not None
            ):
                raise ValueError("SMA snapshot is unsupported.")
        elif (
            self.calculation_version != "rsi_wilder_close_v1"
            or self.period != 14
            or self.threshold is None
        ):
            raise ValueError("RSI snapshot is unsupported.")
        else:
            expected_threshold = Decimal(
                "70" if self.direction == "cross_above" else "30"
            )
            if Decimal(self.threshold) != expected_threshold:
                raise ValueError("RSI threshold snapshot is unsupported.")

        return self


def parse_preset_signal_payload(payload: object) -> PresetSignalPayload:
    try:
        return PresetSignalPayload.model_validate(payload)
    except ValidationError as error:
        raise NotificationPayloadError from error


def _validate_decimal_string(value: object) -> str:
    if not isinstance(value, str) or _DECIMAL_PATTERN.fullmatch(value) is None:
        raise ValueError("Decimal snapshot is invalid.")

    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError("Decimal snapshot is invalid.") from None

    if not decimal_value.is_finite():
        raise ValueError("Decimal snapshot is not finite.")

    return value
