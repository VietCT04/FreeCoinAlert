# Operations

## Purpose

## Signal subscriptions

The application-local signal-subscription limiter is bounded to prevent unbounded memory growth, but its counters are not shared across replicas. A future multi-replica deployment requires an approved shared rate-limit design. The initial preset catalog is seeded by the database migration; it does not contact an external provider at runtime.

This document defines environment configuration, local startup, deployment portability, persistent data, backups, recovery, scheduling, release practices, and operational ownership.

## Current Direction

Hosting is intentionally undecided while the MVP is being built.

The project should run locally and remain portable between managed hosting and a low-cost VPS.

Implemented local startup:

```bash
cp .env.example .env
pnpm dev
```

In PowerShell:

```powershell
Copy-Item .env.example .env
pnpm dev
```

Docker and Docker Compose v2 are required. The stack binds the web, API, and PostgreSQL ports to loopback only. Use `pnpm dev:detached` for detached startup, `pnpm dev:status` for service status, `pnpm dev:logs` for logs, and `pnpm dev:down` for normal shutdown. `pnpm dev:reset` is destructive: it removes all Compose volumes, including the local PostgreSQL data volume.

## Repository Prerequisites and Commands

Repository-level tooling requires Node.js `24.18.0` LTS and pnpm `11.4.0`. The root pnpm workspace currently provides:

```bash
pnpm install
pnpm format
pnpm format:check
pnpm verify
```

The API requires Python `3.14` and uv when it is run outside Compose. Its component project manages its own Python environment and lockfile:

```bash
uv sync --project apps/api
pnpm dev:api
```

After copying `apps/api/.env.example` to a local `apps/api/.env`, direct-host database
operations use `localhost` in `DATABASE_URL`:

```bash
pnpm db:migrate
pnpm db:revision -- -m "describe the change"
```

`db:migrate` explicitly applies Alembic migrations. The local Compose API command waits
for PostgreSQL health and applies `alembic upgrade head` before FastAPI starts; that
behavior is local-development-only and is not a production deployment command.

The frontend component uses Next.js on local port `3000` by default:

```bash
pnpm dev:web
pnpm build:web
pnpm --filter @freecoinalert/web start
```

`pnpm dev` is the default integrated startup command. `pnpm dev:web` and `pnpm dev:api` remain direct component commands for intentional standalone work. `verify` includes the configured frontend formatting, lint, type-check, and build contracts plus backend Ruff and mypy checks. Production process management and hosting remain unresolved.

## Environment Model

At minimum, support separate:

- Local development
- Automated test or CI
- Staging when introduced
- Production

Configuration must come from environment variables or an approved secret manager.

Do not hard-code:

- Database URLs
- Authentication secrets
- Telegram bot token
- Telegram webhook secret
- Binance endpoints when environment override is useful
- Public application URLs
- Provider-specific internal hostnames

Copy `.env.example` to a local `.env` before the first Compose startup. `.env` is ignored by Git. Its PostgreSQL password is only for isolated local development and must never be reused in production. Changing PostgreSQL initialization values after the `postgres_data` volume exists does not recreate the existing database automatically.

Shared variables belong in the root `.env.example` only when more than one application or service consumes them. Component-specific examples belong in `apps/<component>/.env.example` or `services/<component>/.env.example`. Never commit local `.env` files or real credentials.

The API authentication settings are `WEB_ORIGIN`, `SESSION_COOKIE_SECURE`, and `SESSION_TTL_SECONDS`. Local defaults are `http://localhost:3000`, `false`, and `604800` seconds. The web application also receives `NEXT_PUBLIC_API_BASE_URL`, with local default `http://localhost:8000`, through Compose and its component environment example. It is a browser-visible API origin only and must not contain a credential or secret. Before public deployment or multiple API replicas, replace the bounded application-local authentication limiter with a shared, trusted-proxy-aware design; it deliberately uses `request.client.host` and does not trust `X-Forwarded-For`.

`CANDLE_RETENTION_DAYS` defaults to `180`. It defines the intended retention cutoff for current and superseded candle revisions; Issue #48 provides only the bounded cleanup repository operation. No bootstrap, cleanup schedule, reconciliation job, kline stream, or aggregation process is added until Issue #49.

The Telegram connection API also consumes optional public `TELEGRAM_BOT_USERNAME` and positive
`TELEGRAM_LINK_TTL_SECONDS` (local default `600`). The bot username must not include `@` and
may use only Telegram username characters; no Telegram bot token is configured under this
issue. Its five-per-user and ten-per-direct-IP link-creation limits, plus ten-per-user
disconnect limit, are bounded in-process controls. Before public deployment or multiple API
replicas, replace the authentication and Telegram limiters with a shared trusted-proxy-aware
design; they use `request.client.host` and do not trust `X-Forwarded-For`.

The public, credential-free catalog synchronization boundary consumes `BINANCE_SPOT_BASE_URL` (default
`https://api.binance.com`) and `MARKET_CATALOG_MAX_AGE_SECONDS` (default `86400`). Normal API startup does
not contact Binance. An operator may explicitly run `pnpm market:sync`; it requests only the five approved
Spot USDT symbols, commits only after complete validation, and returns non-zero with a safe category on
provider, parsing, or persistence failure. It makes at most one bounded `Retry-After` retry and never runs
as an automatic schedule under this issue.

## Process Model

### Telegram UI Verification Boundary

The local web application includes the authenticated Telegram connection and test-notification UI.
Its normal production path opens a generated Telegram deep link, but implementation work does not open
the link, start the application, make browser or API requests, or contact Telegram. A separate,
maintainer-requested verification pass with configured Telegram credentials is required before marking
the browser flow or provider interaction verified.

The modular-monolith codebase may run as separate processes:

- Web frontend
- API
- Market-data worker
- Notification worker
- Scheduler or scheduled command
- Future historical-analysis worker

Early deployment may combine some processes in one container if lifecycle and failure behavior remain clear.

Do not combine expensive historical analysis with the real-time ingestion loop.

## Containers

Container expectations:

- Reproducible builds
- Pinned runtime versions
- Minimal runtime contents
- Non-root runtime user where practical
- Explicit health checks
- Graceful shutdown
- Restart policies
- No embedded secrets
- Multi-architecture support only when a selected host requires it

Persistent database data must not live only in an ephemeral application container.

The local `db` service uses PostgreSQL `18.4` and the Docker-managed `postgres_data`
volume mounted at `/var/lib/postgresql`. The API receives a `postgresql+psycopg` URL on
the Compose network and depends on the database health check. The initial `users` and
`auth_sessions` schema is owned by Alembic; backup and production migration workflows
remain unresolved.

## Networking

Publicly expose only required HTTP or HTTPS endpoints.

Do not expose:

- PostgreSQL directly to the internet unless protected by an approved network design
- Internal worker endpoints
- Debug ports
- Container-management sockets

Use TLS in production. A reverse proxy such as Caddy or Nginx may be selected when self-hosting.

## Scheduling

Scheduled responsibilities are expected to include:

- Daily candle reconciliation
- Controlled historical backfill commands or jobs
- Cleanup of expired Telegram linking tokens
- Retention cleanup when policies are defined
- Periodic data-quality checks

The selected scheduler must prevent uncontrolled duplicate concurrent runs.

Every scheduled job should be idempotent or protected by a safe locking strategy.

Catalog metadata synchronization is intentionally an explicit manual command until a later approved issue
selects its scheduling and operational ownership.

## Database Backups

Before production launch, define:

- Backup frequency
- Retention period
- Encryption
- Storage location
- Restore procedure
- Recovery point objective
- Recovery time objective
- Who verifies restore tests

A backup policy is incomplete until restoration is tested.

If using a managed database, document what the provider backs up and what remains the application's responsibility.

## Recovery Priorities

Suggested recovery order:

1. Protect database consistency.
2. Restore API access.
3. Restore market-data ingestion and detect the outage gap.
4. Reconcile missing candles.
5. Restore alert evaluation.
6. Restore notification delivery and process pending jobs safely.
7. Resume historical jobs last.

After a market-data outage, do not assume continuity. Detect and repair gaps before evaluating affected candle-close alerts.

## Deployment Provider Selection

Choose a provider only after measuring:

- CPU and memory usage
- WebSocket stability
- Database size and write rate
- Network egress
- Notification throughput
- Operational skill and maintenance time
- Required region and latency
- Backup and recovery options

Likely early options include managed application hosting or a small VPS. The application must not depend on one provider's proprietary behavior unless an approved issue accepts that coupling.

## Release Practices

Before production changes:

- Review database migrations.
- Verify environment variables.
- Run relevant build, lint, type, migration, or test checks according to project policy.
- Confirm rollback or forward-fix approach.
- Avoid deploying market-data schema changes without considering ingestion continuity.
- Record meaningful release and operational concerns.

## Graceful Shutdown

Processes should:

- Stop accepting new work.
- Finish or safely release claimed notification jobs.
- Close WebSocket and database connections.
- Persist required evaluation state.
- Resume safely without duplicate events after restart.

## Data Retention

Canonical and derived candle revisions have an approved initial retention of 180 days. The initial bootstrap target is 150 days, giving enough additional data for a 200-period `4h` warm-up before the earliest retained signal event. Scheduling, execution, backup, archival, and partitioning decisions remain pending.

Separate policies are needed for:

- One-minute candles
- Alert definitions
- Alert events
- Notification attempts
- Telegram connection data
- Audit logs
- Historical-analysis results

Retention changes require database, product, security, and operations review.

## Operational Runbooks Required Later

- Binance WebSocket disconnected
- Market data stale
- Candle gaps detected
- Binance REST rate limited or IP banned
- Telegram delivery backlog
- Telegram bot token exposed
- Database unavailable
- Disk nearly full
- Failed migration
- Restore from backup

## Pending Decisions

## Issue #22 Notification Worker

Use `pnpm dev:notification-worker` to define the local worker command, or the optional `telegram`
Compose profile to start `notification-worker` alongside `telegram-updates`. The worker requires
the internal database configuration and `TELEGRAM_BOT_TOKEN`; normal `pnpm dev` remains free of
Telegram configuration. It claims up to ten available jobs, sleeps about two seconds when idle,
handles shutdown signals, and marks locks older than ten minutes as outcome-unknown failures rather
than resending them.

- Initial hosting provider and region.
- Managed versus self-hosted PostgreSQL.
- Scheduler implementation.
- Backup and restore objectives.
- Deployment and rollback workflow.
- Domain, DNS, and TLS provider.

## Issue #21 Local Telegram Polling

Set local-only `TELEGRAM_BOT_TOKEN` and public `TELEGRAM_BOT_USERNAME` before running
`uv run --project apps/api python -m freecoinalert_api.telegram.poller`. The processor uses
`TELEGRAM_UPDATE_RETENTION_DAYS` with a default of 30. The optional Compose `telegram` profile
uses the same API source and virtual environment, waits for healthy PostgreSQL, and is started with
`pnpm dev:telegram`; use `pnpm dev:telegram-logs` for its logs. Default `pnpm dev` does not start
this process or require Telegram credentials. Do not use local polling alongside a configured
production webhook.

## One-Time Price Alert API Operations

Issue #30 adds bounded in-memory create/delete request windows and a PostgreSQL advisory transaction lock for
same-user active-alert creation. It needs no new process, environment variable, scheduler, migration, provider
contact, or worker. Shared rate limiting and trusted-proxy design are required before multiple replicas or public
launch; operators should observe safe creation, idempotency-conflict, and delete-rejection categories.
# Live-price stream operations

Run the optional local market profile with `pnpm dev:market`, or run the process directly with `pnpm dev:market-stream`; use `pnpm dev:market-logs` for its Compose logs. The default `pnpm dev` stack does not start the stream or contact Binance.

The process uses a PostgreSQL session advisory lock for `freecoinalert:market-stream:binance:spot`, so only one stream can run against an MVP database. It refreshes the controlled catalog at startup and at most every six hours, reconnects when the ready set changes, and uses 1, 2, 4, 8, 16, then at most 30-second reconnect delays with up to 25% jitter. A healthy connection resets backoff after 60 seconds and is proactively replaced before Binance's 24-hour connection limit.

Price-crossing evaluation runs in that same `market-stream` process; no second evaluator, broker, or HTTP relay is
required. Stale or disconnected market state pauses evaluation rather than disabling alerts. Registry refresh
failures retain the last good snapshot and emit a safe operational error.

## Browser Price-Alert Refresh

Issue #33 requires no frontend service or configuration. While visible, the authenticated panel refreshes its first
alert page every 30 seconds for active alerts; pending delivery uses two-second refreshes for at most one minute,
then 15-second refreshes with a manual action. It prevents overlapping requests and stops when alerts are terminal
or the session ends. A maintainer-requested browser/API pass remains necessary before release.
# Candle maintenance

Use `pnpm market:candles-bootstrap` only to explicitly bootstrap the approved catalog, and
`pnpm market:candles-reconcile` only for bounded repair. `CANDLE_BOOTSTRAP_DAYS` defaults to 150
(minimum 35, maximum 180); reconciliation defaults to 24 hours (maximum seven days). The market
profile remains the only always-running market process. No bootstrap, reconciliation, or retention
command was run during implementation.

## Signal event operations

`pnpm signals:backfill` is the explicit future operator command for bounded historical signal rebuilding. It must acquire the market-stream advisory lock, uses `SIGNAL_HISTORY_DAYS=90` (maximum 180), and must never contact Binance. `SIGNAL_LIVE_CATCHUP_MAX_DAYS=7` bounds automatic restart catch-up; signal-event retention is documented as `SIGNAL_EVENT_RETENTION_DAYS=365` without automatic deletion in this issue.
