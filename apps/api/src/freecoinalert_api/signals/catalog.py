import hashlib
from decimal import Decimal

from freecoinalert_api.db.models.signal_preset import SignalPreset
from freecoinalert_api.schemas.signals import (
    SignalParametersResponse,
    SignalPresetResponse,
    SignalSubscriptionPresetResponse,
)


def canonical_configuration_hash(
    *, strategy_type: str, timeframe: str, direction: str, period: int, threshold: Decimal | None, price_input: str, calculation_version: int = 1
) -> str:
    threshold_value = "none" if threshold is None else format(threshold, "f")
    value = f"{strategy_type}|{timeframe}|{direction}|{period}|{threshold_value}|{price_input}|{calculation_version}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parameters_response(preset: SignalPreset) -> SignalParametersResponse:
    return SignalParametersResponse(period=preset.period, threshold=None if preset.threshold is None else format(preset.threshold, "f"), price_input="close")


def public_preset_response(preset: SignalPreset) -> SignalPresetResponse:
    return SignalPresetResponse(code=preset.code, version=preset.version, name=preset.name, description=preset.description, strategy_type=preset.strategy_type, timeframe=preset.timeframe, direction=preset.direction, parameters=parameters_response(preset), status="available")


def subscription_preset_response(preset: SignalPreset) -> SignalSubscriptionPresetResponse:
    return SignalSubscriptionPresetResponse(code=preset.code, version=preset.version, name=preset.name, timeframe=preset.timeframe, direction=preset.direction, parameters=parameters_response(preset))
