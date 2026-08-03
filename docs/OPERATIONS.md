# Operations

## Purpose

This document describes implemented local runtime entry points, settings, manual maintenance, and recovery boundaries. It is not a production deployment guide.

## Runtime Components

The authenticated API owns historical-analysis run creation, listing, detail, cancellation, and owner-scoped report reads. A separate `historical_analysis.worker` process claims bounded runs, prepares canonical snapshots, invokes the pure fixed-preset engine without provider calls, and publishes immutable reports. The explicit `historical_analysis.cleanup` command performs bounded terminal-run retention; it is not scheduled automatically.

The web app, FastAPI API, and PostgreSQL run in the default Compose stack. The API process also starts the signal-feed PostgreSQL listener and local SSE connection manager through its FastAPI lifespan. Optional components are the singleton Binance market stream, Telegram update poller, signal Telegram dispatcher, and historical-analysis worker. Each uses the same database and configuration but is separately started through its Compose profile or direct module command.

## Default Local Stack

`pnpm dev` runs `docker compose up --build`. The core stack starts PostgreSQL, prepares the shared API environment, applies Alembic head, and then starts the API and web app. API and database host ports bind to loopback. `pnpm dev:detached`, `dev:status`, `dev:logs`, and `dev:down` respectively start detached/waited, inspect services, follow logs, and stop/remove orphans. `dev:reset` also removes volumes and is destructive local data removal.

## Local Setup and Preflight

`pnpm dev:setup` resolves the repository root from the cross-platform Node script, copies `.env.example` byte-for-byte to `.env` only when `.env` is absent, and then runs the preflight. An existing `.env` is never modified. `pnpm dev:preflight` validates an existing `.env` without creating, starting, stopping, or waiting for application services. Both commands use only Node built-ins, never contact Binance or Telegram, and report variable names and corrective actions without printing values.

The parser ignores blank lines and comments, accepts `KEY=VALUE` with optional matching single or double quotes, rejects malformed non-comment lines, performs no shell expansion or file execution, and lets process-environment values override the corresponding `.env` values. Required local setup keys are `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `WEB_PORT`, `API_PORT`, `POSTGRES_PORT`, `NEXT_PUBLIC_API_BASE_URL`, `WEB_ORIGIN`, `SESSION_COOKIE_SECURE`, `BINANCE_SPOT_BASE_URL`, `BINANCE_SPOT_WS_BASE_URL`, `LOCAL_ENABLE_TELEGRAM`, `LOCAL_CANDLE_BOOTSTRAP_DAYS`, and `LOCAL_STARTUP_TIMEOUT_SECONDS`. Ports must be distinct integers from 1 through 65535; HTTP URLs use `http` or `https`; the Binance WebSocket URL uses `ws` or `wss`; booleans are exact lowercase `true` or `false`; candle bootstrap is 35 through 180 days; and startup timeout is 60 through 7,200 seconds.

Docker availability is checked with `docker version`, `docker compose version`, and `docker compose config --quiet`. Compose v2 is required for completed-service dependencies, `up --wait`, and JSON service inspection. The preflight inspects currently running Compose services before trying to bind each unused exposed port on `127.0.0.1`, so an existing matching `web`, `api`, or `db` service does not produce a false port conflict. It does not start the stack or claim readiness. Local profile selection always includes `market`, includes `telegram` only when `LOCAL_ENABLE_TELEGRAM=true` and its username/token are valid, and reserves `historical-analysis` as a future conditional profile. Telegram is disabled by default, and a disabled configuration must not retain a bot token.

## Optional Compose Profiles

`pnpm dev:market` starts the core stack and the `market` profile. The profile runs `market-catalog-init` and `candle-bootstrap-init` before `market-stream`. `pnpm dev:telegram` starts the core stack and the `telegram` profile containing `telegram-updates`, `signal-telegram-dispatcher`, and `notification-worker`. `docker compose --profile historical-analysis up --build` starts the core stack and the real `historical-analysis-worker`; `pnpm analysis:worker` runs it directly and `pnpm analysis:cleanup` runs the one-shot cleanup command. Their log commands follow the matching profile service. The market catalog and candle initialization services contact Binance; the market stream contacts Binance; the poller and notification worker contact Telegram when configured; the signal dispatcher and historical-analysis worker contact only PostgreSQL. Initialization services are one-shot; the profile workers are long-running except for explicit cleanup.

## Compose Initialization and Dependencies

The shared `x-api-common` Compose extension centralizes the API image, source mount, persistent `api_venv` volume, database URL, and `init: true`. `api-prepare` runs `uv sync --frozen` once. `db-migrate` waits for a healthy PostgreSQL service and successful preparation before running `uv run --frozen alembic upgrade head`. All Python services wait for `api-prepare` through this migration dependency and use `uv run --frozen` without running `uv sync` themselves.

The startup graph is:

```text
db (healthy)
└── api-prepare (completed)
    └── db-migrate (completed)
        ├── api (healthy) ── web
        ├── telegram-updates
        ├── notification-worker
        ├── signal-telegram-dispatcher
        ├── historical-analysis-worker
        └── market-catalog-init (completed)
            └── candle-bootstrap-init (completed)
                └── market-stream
```

`api-prepare`, `db-migrate`, `market-catalog-init`, and `candle-bootstrap-init` use `restart: "no"` through their one-shot lifecycle. A failed preparation or migration blocks dependent services; catalog or candle initialization failure blocks the market stream. Telegram and historical-analysis profiles remain optional and do not block the core stack. PostgreSQL and dependency volumes remain persistent, and repeating startup does not remove volumes or create duplicate logical initialization rows. The catalog initializer and candle bootstrap use the existing idempotent/gap-based paths.

## Root Commands

| Command | Purpose / prerequisites | External contact | Mode |
| --- | --- | --- | --- |
| `pnpm dev:setup` | Create `.env` only if absent and run local setup/preflight validation. | None | One-shot |
| `pnpm dev:preflight` | Validate existing `.env`, Docker/Compose, configuration, and ports without startup. | None | One-shot |
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
| `pnpm analysis:worker` | Claim, execute, recover, and publish bounded owner-scoped historical-analysis reports; database required. | Database only | Long-running |
| `pnpm analysis:cleanup` | Delete terminal historical-analysis runs older than configured retention in one bounded batch. | Database | One-shot |

Formatting, lint, typecheck, build, and verification scripts exist for development but are not operational startup commands.

## API Module Entry Points

The commands invoke `freecoinalert_api.market_data.catalog_sync`, `.market_data.stream`, `.market_data.candles.bootstrap`, `.market_data.candles.reconciliation`, `.signals.backfill`, `.telegram.poller`, `.notifications.signal_dispatcher`, `.notifications.worker`, `.historical_analysis.worker`, and `.historical_analysis.cleanup`. Direct API startup uses FastAPI with `main.py`; the API lifespan starts `.signals.feed_listener` without a separate process command.

## Environment Configuration

Historical-analysis range, version, active-run, request, and pure-engine resource limits are fixed server policy/constants in the API package. `CANDLE_RETENTION_DAYS` bounds the warm-up validation. The worker defaults to a 2-second poll, one claimed run, a 600-second stale-claim threshold, and one simulation at a time. `HISTORICAL_ANALYSIS_WORKER_POLL_SECONDS`, `HISTORICAL_ANALYSIS_WORKER_CLAIM_LIMIT` (1 through 4), `HISTORICAL_ANALYSIS_WORKER_STALE_SECONDS` (at least 60), `HISTORICAL_ANALYSIS_RETENTION_DAYS` (at least 1), and `HISTORICAL_ANALYSIS_CLEANUP_BATCH_SIZE` (1 through 1,000) configure the worker and explicit cleanup.

`DATABASE_URL` is required and secret for direct-host API use; Compose builds its internal database URL from the local PostgreSQL settings. `WEB_ORIGIN` defaults to `http://localhost:3000`; `SESSION_COOKIE_SECURE` defaults false; `SESSION_TTL_SECONDS` defaults 604800. Telegram username/token and TTL/retention are described in [TELEGRAM.md](TELEGRAM.md). Binance URLs are public provider settings. Market settings and defaults are in [MARKET_DATA.md](MARKET_DATA.md). The Compose market profile maps `LOCAL_CANDLE_BOOTSTRAP_DAYS` to `CANDLE_BOOTSTRAP_DAYS` for the bounded initialization service and defaults it to 35 days; the accepted range is 35 through 180 days. `LOCAL_ENABLE_TELEGRAM=false` disables Telegram by default; when true, `TELEGRAM_BOT_USERNAME` and `TELEGRAM_BOT_TOKEN` are required, and the setup/preflight flow does not generate, rotate, or print either value. `LOCAL_STARTUP_TIMEOUT_SECONDS` defaults to 1,800 and is validated from 60 through 7,200 seconds for the approved local startup flow; the setup/preflight command itself does not start services or consume the timeout. `SIGNAL_LIVE_CATCHUP_MAX_DAYS=7` is reserved configuration with no automatic catch-up implementation; `SIGNAL_HISTORY_DAYS=90` only bounds the placeholder backfill coverage check; `SIGNAL_EVENT_RETENTION_DAYS=365` has no cleanup implementation. Signal SSE defaults are 2 connections per user, 500 per process, queue size 100, 15-second heartbeats, 60-second session revalidation, and 7-day stream-cursor retention; these limits are configured by `SIGNAL_SSE_*` and `SIGNAL_STREAM_RETENTION_DAYS`. Signal Telegram fan-out defaults are batch size 100, claim limit 10, 2-second polling, and a 900-second maximum delivery age; these limits are configured by `SIGNAL_TELEGRAM_FANOUT_*`. Signal Telegram-delivery preference mutations use a process-local limit of 30 per user per 15 minutes. Environment examples contain names and safe defaults only; never commit secrets.

`NEXT_PUBLIC_API_BASE_URL` is the browser-visible API origin and must contain no secret. The browser signal and historical-analysis sections need no separate process, provider credential, audio asset, chart dependency, or runtime configuration beyond the existing API origin and credentialed CORS/SSE proxy requirements. Historical-analysis browser controls use the existing authenticated API and CSRF token; they do not contact Binance or Telegram from the browser or require provider configuration in the web app.

While visible, native EventSource uses the server retry value. After 60 seconds of disconnection, the browser shows the disconnected state, refreshes the first history page every 30 seconds, and offers `Reconnect live updates`; fallback entries are merged without live highlight or sound. Polling stops when SSE reconnects or the document becomes hidden.

## Database Migrations

The current chain also adds the owner-scoped `historical_analysis_runs`, `historical_analysis_datasets`, `historical_analysis_dataset_candles`, `historical_analysis_reports`, `historical_analysis_trades`, and `historical_analysis_equity_points` tables. Their migrations create no work rows, do not call Binance, and do not read candle history. Database backup, restore, and production rollout automation remain unimplemented.

Apply migrations manually through the release/development workflow with `pnpm db:migrate`, or let the local Compose `db-migrate` one-shot service apply them before dependent services start. The preceding signal Telegram migrations add the per-subscription delivery columns, immutable state-history table, dispatch table, and preset-signal outbox references. Their data steps create one disabled baseline state row per existing subscription and no dispatch rows or notification work for existing signal history. The historical-analysis migrations add request/lifecycle state, canonical dataset/snapshot tables, and immutable report series only; they create no work rows and perform no candle or provider work. The local Compose migration service is not production migration automation. Database backup, restore, and production rollout automation are not implemented.

## Market Catalog Synchronization

`market-catalog-init` is the one-shot `market`-profile prerequisite for the stream. It calls Binance only for the fixed catalog, preserves the last valid metadata on failure, and returns non-zero so the dependent candle bootstrap and stream do not start. `market:sync` remains the equivalent direct operator command. Catalog synchronization is not scheduled by a separate service.

## Market Stream

Run one `market-stream` owner only. The Compose `market` profile starts it only after successful catalog and candle initialization. It owns advisory lock `freecoinalert:market-stream:binance:spot`, refreshes catalog, reconnects with bounded backoff, and performs its implemented recent reconciliation. Two processes do not horizontally share stream ownership.

## Candle Bootstrap and Reconciliation

Use bootstrap for a new/empty bounded history and reconciliation for missing recent data. The Compose `candle-bootstrap-init` service reuses the existing gap-based bootstrap, requests the bounded `LOCAL_CANDLE_BOOTSTRAP_DAYS` range (35 days by default, maximum 180), and runs after catalog initialization. `market:candles-bootstrap` remains the direct command and reads `CANDLE_BOOTSTRAP_DAYS` (default 150 for direct-host use). Reconciliation maximum is 168 hours. Both modes acquire the market singleton lock, page at 1,000 minutes, and must not run concurrently with the stream owner.

## Signal Backfill

`signals:backfill` is an explicit singleton-protected future historical-rebuild boundary. It checks product markets and current complete `1h`/`4h` coverage inside `SIGNAL_HISTORY_DAYS`, logs startup, then reports `evaluator_rebuild_required`; it does not currently create or rebuild signal events and does not contact Binance or Telegram. If a future rebuild creates `backfilled=true` events, their dispatch rows are skipped and are not delivered retroactively. The subscription Telegram-delivery preference and signal fan-out are ordinary API/database work plus the separately runnable dispatcher; neither path contacts Telegram.

## Telegram Poller and Notification Worker

Start the poller only when a valid bot token is available; it cannot coexist with a Telegram webhook. The notification worker normally also uses that token for provider requests, but can safely claim jobs without it and mark them `failed` with `telegram_not_configured`. The signal dispatcher needs only database configuration and does not contact Telegram. The notification worker independently claims and recovers all three supported notification kinds; none of these processes run in the default profile.

## Singleton and Concurrency Controls

PostgreSQL advisory locks serialize market streaming, candle maintenance, and signal backfill around the market-stream lock key. The signal-feed listener uses one dedicated PostgreSQL `LISTEN` connection per API process; each replica receives notifications independently and owns only its local SSE connections. API rate limits and feed connection limits are in-memory per process, so they are not a distributed abuse-control or aggregate connection solution. Provider REST requests are serialized inside the implemented maintenance flows.

## Retention and Maintenance

Historical-analysis cleanup is explicit: `pnpm analysis:cleanup` deletes only terminal runs older than `HISTORICAL_ANALYSIS_RETENTION_DAYS`, oldest first, up to `HISTORICAL_ANALYSIS_CLEANUP_BATCH_SIZE`. Database cascades remove their datasets, snapshot candles, reports, trades, and equity points; queued/running runs are never eligible. The command has no scheduler and must be placed in any operator-controlled maintenance schedule deliberately.

The code has candle-revision cleanup bounded by `CANDLE_RETENTION_DAYS`, processed Telegram-update cleanup bounded by `TELEGRAM_UPDATE_RETENTION_DAYS`, and signal-event retention settings. The API listener performs at most one signal-feed stream-cursor cleanup pass per 24 hours, deleting no more than 10,000 rows older than `SIGNAL_STREAM_RETENTION_DAYS` in one transaction. It never deletes the referenced signal event. Signal dispatch and preset-signal outbox rows have no automatic cleanup. No scheduler invokes generic cleanup automatically. Run only implemented explicit maintenance under an operator-controlled schedule.

## Startup and Shutdown Expectations

Start PostgreSQL before direct API commands. API startup itself does not contact providers. Stop long-running processes gracefully so their connections and advisory locks close. Restarting market processing relies on persisted current state and idempotent repositories rather than replaying raw trade history.

Run `pnpm dev:setup` before the local Compose workflow or `pnpm dev:preflight` when checking an existing configuration. These commands do not replace the explicit Compose start/stop commands and do not provide final service-readiness evidence.

## Recovery Runbooks

- Stale market data: inspect operational state/logs, confirm the sole stream owner, restore it, then use bounded reconciliation if gaps remain.
- Candle gap or failed repair: use `market:candles-reconcile`; use bootstrap only for the bounded historical range.
- Telegram configuration missing: provide the username for links and secret token for poller/worker when provider behavior is desired; the API remains available without them and a tokenless notification worker records `telegram_not_configured` safely.
- Stuck notification claims: inspect the persisted job state. The worker detects stale claims and terminally records `telegram_delivery_outcome_unknown`; it does not resume or requeue an uncertain provider send.
- Stuck signal fan-out: inspect `signal_telegram_dispatches` for `processing`, `retry_wait`, `failed`, `skipped`, counts, cursor, and safe failure code. The dispatcher requeues stale database-only claims, retries bounded database failures, and never retries beyond `max_attempts` or creates jobs older than the configured maximum age.
- Historical-analysis cancellation: a queued run is cancelled immediately; a running run records a cancellation request and the worker acknowledges it before dataset preparation, before simulation, after simulation, or before report publication. Do not treat a non-succeeded run as a completed report.
- Historical-analysis worker recovery: start `pnpm analysis:worker` or the `historical-analysis` Compose profile. It claims due rows with row locks, requeues stale database-only work with bounded backoff, fails exhausted attempts safely, validates current snapshots immediately before simulation and publication, and never contacts Binance or mutates live alert/signal/delivery state.
- Historical-analysis cleanup: run `pnpm analysis:cleanup` explicitly after confirming the configured retention and batch size. It deletes only terminal runs and their cascaded report/dataset rows; it does not delete active work.
- Provider rate limit: stop repeated commands, honor Retry-After, and wait for the bounded retry path; treat 418 as an incident.

## Production Gaps

No implemented production topology, deployment automation, backup automation, distributed rate limiter, queue broker, cron scheduler, horizontal stream ownership, or managed monitoring stack exists. A production reverse proxy must disable buffering for `/signal-feed/stream`, preserve `Cache-Control: no-transform`, use a read timeout longer than the 15-second heartbeat, pass cookies/CORS headers, and avoid requiring WebSocket upgrade headers. The browser closes the stream while hidden and recovers history before reopening it.

## Verification Status

No setup/preflight script, processes, migrations, maintenance commands, providers, or Compose services were run for this documentation audit.
