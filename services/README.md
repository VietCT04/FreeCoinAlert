# Services

This directory contains separately runnable background processes.

The market-data and notification services will be introduced only by their approved implementation issues.

The local Telegram update processor remains part of `apps/api` because it shares that package's
configuration, persistence, and linking business logic; run it with
`uv run --project apps/api python -m freecoinalert_api.telegram.poller` when explicitly needed.

The durable Telegram test-notification worker also remains in `apps/api`; run it with
`uv run --project apps/api python -m freecoinalert_api.notifications.worker` only when explicitly
needed. It is not a separate service project and must not be started for routine implementation.
