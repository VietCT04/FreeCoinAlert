from datetime import UTC, datetime

from freecoinalert_api.notifications.payloads import PresetSignalPayload


def format_price_alert_message(payload: dict[str, object]) -> str:
    direction = payload.get("direction")
    phrase = "crossed above" if direction == "cross_above" else "crossed below"
    triggered_at = datetime.fromisoformat(str(payload["triggeredAt"]))
    timestamp = triggered_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        "FreeCoinAlert price alert\n\n"
        f"{payload['symbol']} {phrase} {payload['targetPrice']} {payload['quoteAsset']}.\n"
        f"Observed price: {payload['triggerPrice']} {payload['quoteAsset']}\n"
        f"Time: {timestamp}"
    )


def format_preset_signal_message(payload: PresetSignalPayload) -> str:
    if payload.strategy_type == "price_sma_cross":
        left_label = "Close"
        right_label = "SMA 200"
    else:
        left_label = "RSI 14"
        right_label = "Threshold"

    direction = "above" if payload.direction == "cross_above" else "below"
    candle_closed_at = payload.candle_close_time.astimezone(UTC).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    return (
        "FreeCoinAlert preset signal\n\n"
        f"{payload.symbol} · {payload.preset_name}\n"
        f"{payload.timeframe} candle crossed {direction}.\n\n"
        "Previous:\n"
        f"{left_label}: {payload.previous_left_value}\n"
        f"{right_label}: {payload.previous_right_value}\n\n"
        "Current:\n"
        f"{left_label}: {payload.current_left_value}\n"
        f"{right_label}: {payload.current_right_value}\n"
        f"Close: {payload.candle_close_price} {payload.quote_asset}\n\n"
        f"Candle closed: {candle_closed_at}\n"
        f"Preset: {payload.preset_code} v{payload.preset_version}\n"
        f"Calculation version: {payload.calculation_version}\n\n"
        "Informational only — not financial advice."
    )
