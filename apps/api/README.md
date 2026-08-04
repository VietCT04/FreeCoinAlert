# FreeCoinAlert API

## Purpose

`apps/api` is the FastAPI application. It owns HTTP routes, owner-scoped historical-analysis run and report persistence, the bounded historical-analysis worker and cleanup command, the pure deterministic historical-analysis engine, an internal canonical dataset service, and the runnable market-data, Telegram-update, signal-dispatch, and notification-worker modules.

## Prerequisites and Setup

Use CPython `3.14` and [uv](https://docs.astral.sh/uv/). From this directory, copy [`.env.example`](.env.example) to `.env` for direct-host development, then install the locked environment:

```bash
uv sync
```

Repository-wide Compose setup and shared environment values are in [`../../.env.example`](../../.env.example) and [Operations](../../docs/OPERATIONS.md). From the repository root, `pnpm dev:setup` creates the ignored root `.env` only when it is absent and performs the dependency-free local preflight; `pnpm dev:all` then runs the validated full-stack startup and readiness flow. `pnpm dev:preflight` repeats validation without starting a process or contacting a provider. Compose prepares the shared `api_venv` volume once through `api-prepare`, then applies migrations through `db-migrate` before API or worker processes start; direct-host development keeps its own explicit `uv sync` setup.

## Entry Points

Run these from the repository root unless noted otherwise:

```bash
pnpm dev:all
pnpm dev:all:detached
pnpm dev:all:logs
pnpm dev:status
pnpm dev:down
pnpm dev:reset
pnpm dev:api
pnpm db:migrate
pnpm db:revision -- -m "description"
pnpm market:sync
pnpm dev:market
pnpm dev:market-stream
pnpm market:candles-bootstrap
pnpm market:candles-reconcile
pnpm signals:backfill
pnpm dev:telegram
pnpm dev:telegram-updates
pnpm dev:notification-worker
pnpm dev:signal-telegram-dispatcher
pnpm analysis:worker
pnpm analysis:cleanup
```

`dev:all` starts the enabled Compose profiles, waits for completed initialization and required health, and prints a normalized readiness summary before following logs. `dev:all:detached` performs the same startup and readiness checks without attaching logs; `dev:all:logs` follows logs for enabled profiles; `dev:down` preserves volumes; and `dev:reset` requires explicit confirmation. `market:sync`, `dev:market-stream`, `market:candles-bootstrap`, and `market:candles-reconcile` contact Binance. `dev:telegram-updates` and `dev:notification-worker` contact Telegram when configured; the worker also records a safe terminal failure when bot configuration is missing. `dev:signal-telegram-dispatcher` contacts only PostgreSQL and creates durable preset-signal outbox jobs; it does not contact Telegram. `signals:backfill` is a placeholder validation boundary, not automatic signal catch-up. API startup also starts the PostgreSQL signal-feed listener and bounded local SSE manager through FastAPI lifespan. See [Operations](../../docs/OPERATIONS.md) before using these commands.

The isolated E2E overlay uses this same API image and real application modules with a dedicated PostgreSQL database, deterministic seed, internal control service, and provider simulator. E2E-only seed/control/gate entry points refuse to run unless E2E mode and an `_e2e` database are configured; no E2E route is mounted in the public API. See [Testing](../../docs/TESTING.md) for the boundary and [Operations](../../docs/OPERATIONS.md) for the isolated Compose invocation.

## Authoritative Documentation

- [API contracts](../../docs/API.md)
- [Database schema and migrations](../../docs/DATABASE.md)
- [Operations and configuration](../../docs/OPERATIONS.md)
- [Market data](../../docs/MARKET_DATA.md)
- [Telegram and delivery](../../docs/TELEGRAM.md)
- [Alerts and signal occurrences](../../docs/ALERTS.md)
- [Strategies](../../docs/STRATEGIES.md)
- [Security](../../docs/SECURITY.md)
- [Signal feed API and recovery](../../docs/API.md#historical-signal-feed)
- [Signal subscription delivery preference](../../docs/API.md#signal-presets-and-subscriptions)
- [Historical-analysis run API](../../docs/API.md#historical-analysis-runs)

The historical-analysis API stores bounded authenticated run requests and exposes owner-only immutable reports, trades, and equity pages after the separate worker publishes a successful result. The worker validates canonical coverage, runs the pure engine from immutable snapshots without provider calls, and publishes reports atomically. The Compose `historical-analysis` profile starts that real worker after `db-migrate`; `analysis:cleanup` is an explicit bounded terminal-run retention command and is not scheduled automatically.
