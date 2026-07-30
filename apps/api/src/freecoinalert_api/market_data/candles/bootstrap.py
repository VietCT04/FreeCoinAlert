import asyncio
from freecoinalert_api.core.config import get_settings
from freecoinalert_api.market_data.candles.reconciliation import reconcile_recent


def main() -> None:
    settings = get_settings()
    raise SystemExit(asyncio.run(reconcile_recent(hours=settings.candle_bootstrap_days * 24, kind="bootstrap")))


if __name__ == "__main__":
    main()
