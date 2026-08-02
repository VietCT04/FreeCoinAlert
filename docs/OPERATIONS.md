# Operations

## Purpose

This document describes implemented local runtime entry points, settings, manual maintenance, and recovery boundaries. It is not a production deployment guide.

## Runtime Components

The web app, FastAPI API, and PostgreSQL run in the default Compose stack. The API process also starts the signal-feed PostgreSQL listener and local SSE connection manager through its FastAPI lifespan. Optional components are the singleton Binance market stream, Telegram update poller, signal Telegram dispatcher, and notification worker. Each uses the same database and configuration but is separately started.

## Default Local Stack

`pnpm dev` runs `docker compose up --build`: web, API, and PostgreSQL. The API container applies Alembic head before FastAPI starts in local development. API and database host ports bind to loopback. `pnpm dev:detached`, `dev:status`, `dev:logs`, and `dev:down` respectively start detached/waited, inspect services, follow logs, and stop/remove orphans. `dev:reset` also removes volumes and is destructive local data removal.

## Optional Compose Profiles

`pnpm dev:market` starts the `market` profile containing `market-stream`. `pnpm dev:telegram` starts the `telegram` profile containing `telegram-updates`, `signal-telegram-dispatcher`, and `notification-worker`. Their log commands follow the matching profile service. The market stream contacts Binance; the poller and notification worker contact Telegram when configured; the signal dispatcher contacts only PostgreSQL. All are long-running.

## Root Commands

| Command | Purpose / prerequisites | External contact | Mode |
| --- | --- | --- | --- |
| `pnpm dev:web` / `pnpm dev:api` | Direct development servers; API needs database settings. | No provider by itself | Long-running |
| `pnpm db:migrate` | Apply Alembic head; database required. | Database | One-shot |
| `pnpm market:sync` | Synchronize five-symbol catalog; database required. | Binance REST | One-shot |
| `pnpm dev:market-stream` | Run singleton stream; database/catalog required. | Binance WS/REST | Long-running |
| `pnpm market:candles-bootstrap` | Bootstrap bounded history. | Binance REST | One-shot |
| `pnpm market:candles-reconcile` | Repair bounded missing ranges. | Binance REST | One-shot |
| `pnpm signals:backfill` | Check singleton/coverage boundary for a future bounded rebuild. | Database | One-shot |
| `pnpm dev:telegram-updates` | Run private-message link poller; bot token required. | Telegram | Long-running |
| `pnpm dev:signal-telegram-dispatcher` | Fan out eligible live signal occurrences into durable outbox jobs; database required. | Database | Long-running |
| `pnpm dev:notification-worker` | Claim and send durable test, price-alert, and preset-signal jobs; database required, bot token needed for provider requests. | Telegram when configured | Long-running |

Formatting, lint, typecheck, build, and verification scripts exist for development but are not operational startup commands.

## API Module Entry Points

The commands invoke `freecoinalert_api.market_data.catalog_sync`, `.market_data.stream`, `.market_data.candles.bootstrap`, `.market_data.candles.reconciliation`, `.signals.backfill`, `.telegram.poller`, `.notifications.signal_dispatcher`, and `.notifications.worker`. Direct API startup uses FastAPI with `main.py`; the API lifespan starts `.signals.feed_listener` without a separate process command.

## Environment Configuration

`DATABASE_URL` is required and secret. `WEB_ORIGIN` defaults to `http://localhost:3000`; `SESSION_COOKIE_SECURE` defaults false; `SESSION_TTL_SECONDS` defaults 604800. Telegram username/token and TTL/retention are described in [TELEGRAM.md](TELEGRAM.md). Binance URLs are public provider settings. Market settings and defaults are in [MARKET_DATA.md](MARKET_DATA.md). `SIGNAL_LIVE_CATCHUP_MAX_DAYS=7` is reserved configuration with no automatic catch-up implementation; `SIGNAL_HISTORY_DAYS=90` only bounds the placeholder backfill coverage check; `SIGNAL_EVENT_RETENTION_DAYS=365` has no cleanup implementation. Signal SSE defaults are 2 connections per user, 500 per process, queue size 100, 15-second heartbeats, 60-second session revalidation, and 7-day stream-cursor retention; these limits are configured by `SIGNAL_SSE_*` and `SIGNAL_STREAM_RETENTION_DAYS`. Signal Telegram fan-out defaults are batch size 100, claim limit 10, 2-second polling, and a 900-second maximum delivery age; these limits are configured by `SIGNAL_TELEGRAM_FANOUT_*`. Signal Telegram-delivery preference mutations use a process-local limit of 30 per user per 15 minutes. Environment examples contain names and safe defaults only; never commit secrets.

`NEXT_PUBLIC_API_BASE_URL` is the browser-visible API origin and must contain no secret. The browser signal section needs no separate process, provider credential, audio asset, or runtime configuration beyond the existing API origin and credentialed CORS/SSE proxy requirements.

While visible, native EventSource uses the server retry value. After 60 seconds of disconnection, the browser shows the disconnected state, refreshes the first history page every 30 seconds, and offers `Reconnect live updates`; fallback entries are merged without live highlight or sound. Polling stops when SSE reconnects or the document becomes hidden.

## Database Migrations

Apply migrations manually through the release/development workflow with `pnpm db:migrate`. The current chain head adds the per-subscription Telegram-delivery columns, immutable state-history table, dispatch table, and preset-signal outbox references. Its data steps create one disabled baseline state row per existing subscription and no dispatch rows or notification work for existing signal history. The local Compose API startup is not production migration automation. Database backup, restore, and production rollout automation are not implemented.

## Market Catalog Synchronization

Run `market:sync` before expecting catalog readiness. It is one-shot, calls Binance only for the fixed catalog, and preserves the last valid metadata on failure. It is not scheduled by a separate service.

## Market Stream

Run one `market-stream` owner only. It owns advisory lock `freecoinalert:market-stream:binance:spot`, refreshes catalog, reconnects with bounded backoff, and performs its implemented recent reconciliation. Two processes do not horizontally share stream ownership.

## Candle Bootstrap and Reconciliation

Use bootstrap for a new/empty bounded history and reconciliation for missing recent data. Bootstrap maximum is 180 days; reconciliation maximum is 168 hours. Both acquire the market singleton lock, page at 1,000 minutes, and must not run concurrently with the stream owner.

## Signal Backfill

`signals:backfill` is an explicit singleton-protected future historical-rebuild boundary. It checks product markets and current complete `1h`/`4h` coverage inside `SIGNAL_HISTORY_DAYS`, logs startup, then reports `evaluator_rebuild_required`; it does not currently create or rebuild signal events and does not contact Binance or Telegram. If a future rebuild creates `backfilled=true` events, their dispatch rows are skipped and are not delivered retroactively. The subscription Telegram-delivery preference and signal fan-out are ordinary API/database work plus the separately runnable dispatcher; neither path contacts Telegram.

## Telegram Poller and Notification Worker

Start the poller only when a valid bot token is available; it cannot coexist with a Telegram webhook. The notification worker normally also uses that token for provider requests, but can safely claim jobs without it and mark them `failed` with `telegram_not_configured`. The signal dispatcher needs only database configuration and does not contact Telegram. The notification worker independently claims and recovers all three supported notification kinds; none of these processes run in the default profile.

## Singleton and Concurrency Controls

PostgreSQL advisory locks serialize market streaming, candle maintenance, and signal backfill around the market-stream lock key. The signal-feed listener uses one dedicated PostgreSQL `LISTEN` connection per API process; each replica receives notifications independently and owns only its local SSE connections. API rate limits and feed connection limits are in-memory per process, so they are not a distributed abuse-control or aggregate connection solution. Provider REST requests are serialized inside the implemented maintenance flows.

## Retention and Maintenance

The code has candle-revision cleanup bounded by `CANDLE_RETENTION_DAYS`, processed Telegram-update cleanup bounded by `TELEGRAM_UPDATE_RETENTION_DAYS`, and signal-event retention settings. The API listener performs at most one signal-feed stream-cursor cleanup pass per 24 hours, deleting no more than 10,000 rows older than `SIGNAL_STREAM_RETENTION_DAYS` in one transaction. It never deletes the referenced signal event. Signal dispatch and preset-signal outbox rows have no automatic cleanup. No scheduler invokes generic cleanup automatically. Run only implemented explicit maintenance under an operator-controlled schedule.

## Startup and Shutdown Expectations

Start PostgreSQL before direct API commands. API startup itself does not contact providers. Stop long-running processes gracefully so their connections and advisory locks close. Restarting market processing relies on persisted current state and idempotent repositories rather than replaying raw trade history.

## Recovery Runbooks

- Stale market data: inspect operational state/logs, confirm the sole stream owner, restore it, then use bounded reconciliation if gaps remain.
- Candle gap or failed repair: use `market:candles-reconcile`; use bootstrap only for the bounded historical range.
- Telegram configuration missing: provide the username for links and secret token for poller/worker when provider behavior is desired; the API remains available without them and a tokenless notification worker records `telegram_not_configured` safely.
- Stuck notification claims: inspect the persisted job state. The worker detects stale claims and terminally records `telegram_delivery_outcome_unknown`; it does not resume or requeue an uncertain provider send.
- Stuck signal fan-out: inspect `signal_telegram_dispatches` for `processing`, `retry_wait`, `failed`, `skipped`, counts, cursor, and safe failure code. The dispatcher requeues stale database-only claims, retries bounded database failures, and never retries beyond `max_attempts` or creates jobs older than the configured maximum age.
- Provider rate limit: stop repeated commands, honor Retry-After, and wait for the bounded retry path; treat 418 as an incident.

## Production Gaps

No implemented production topology, deployment automation, backup automation, distributed rate limiter, queue broker, cron scheduler, horizontal stream ownership, or managed monitoring stack exists. A production reverse proxy must disable buffering for `/signal-feed/stream`, preserve `Cache-Control: no-transform`, use a read timeout longer than the 15-second heartbeat, pass cookies/CORS headers, and avoid requiring WebSocket upgrade headers. The browser closes the stream while hidden and recovers history before reopening it.

## Verification Status

No processes, migrations, maintenance commands, providers, or Compose services were run for this documentation audit.
