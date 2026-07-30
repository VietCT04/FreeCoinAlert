from datetime import datetime


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
