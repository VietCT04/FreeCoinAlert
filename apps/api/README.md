# FreeCoinAlert API

## Purpose

`apps/api` is the FastAPI application. It owns HTTP routes, owner-scoped historical-analysis run persistence, and the runnable market-data, Telegram-update, signal-dispatch, and notification-worker modules.

## Prerequisites and Setup

Use CPython `3.14` and [uv](https://docs.astral.sh/uv/). From this directory, copy [`.env.example`](.env.example) to `.env` for direct-host development, then install the locked environment:

```bash
uv sync
```

Repository-wide Compose setup and shared environment values are in [`../../.env.example`](../../.env.example) and [Operations](../../docs/OPERATIONS.md).

## Entry Points

Run these from the repository root unless noted otherwise:

```bash
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
```

`market:sync`, `dev:market-stream`, `market:candles-bootstrap`, and `market:candles-reconcile` contact Binance. `dev:telegram-updates` and `dev:notification-worker` contact Telegram when configured; the worker also records a safe terminal failure when bot configuration is missing. `dev:signal-telegram-dispatcher` contacts only PostgreSQL and creates durable preset-signal outbox jobs; it does not contact Telegram. `signals:backfill` is a placeholder validation boundary, not automatic signal catch-up. API startup also starts the PostgreSQL signal-feed listener and bounded local SSE manager through FastAPI lifespan. See [Operations](../../docs/OPERATIONS.md) before using these commands.

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

The historical-analysis API currently stores bounded authenticated run requests and safe lifecycle metadata only. It has no dataset, simulation, worker, report, or provider entry point.
