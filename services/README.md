# Services

This directory contains separately runnable background processes.

The market-data and notification services will be introduced only by their approved implementation issues.

The local Telegram update processor remains part of `apps/api` because it shares that package's
configuration, persistence, and linking business logic; run it with
`uv run --project apps/api python -m freecoinalert_api.telegram.poller` when explicitly needed.

The durable Telegram test-notification worker also remains in `apps/api`; run it with
`uv run --project apps/api python -m freecoinalert_api.notifications.worker` only when explicitly
needed. It is not a separate service project and must not be started for routine implementation.

The centralized Binance Spot market stream also remains in `apps/api` so it can reuse the controlled
catalog and persistence boundaries. Run `uv run --project apps/api python -m freecoinalert_api.market_data.stream`
only when explicitly needed, or use the optional Compose `market` profile. It owns provider connectivity and
normalized events only; alert evaluation and notification delivery are not part of this process in Issue #31.
