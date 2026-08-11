# US-0016 — Admin Operations Console

## Status

Approved for planning. Implementation requires a separately approved technical solution comment on each child issue before code changes begin.

## User story

As a FreeCoinAlert administrator, I want one protected operations page where I can see data readiness, running components, component health, jobs and queues, recent operational logs, provider health, and safe system information, so that I can understand whether the platform is healthy without opening Docker, PostgreSQL, or several terminal sessions.

## Problem

FreeCoinAlert now has multiple long-running processes and durable data flows: API, market streaming, historical candle backfill, historical analysis, notifications, signal delivery, Telegram polling, provider integrations, and canonical candle storage. Operational state is spread across process logs, database tables, health endpoints, and local orchestration output.

The current `/health` endpoint is intentionally minimal and only establishes that the API process itself can answer a request. It does not explain whether market data is fresh, historical data is complete, workers are processing work, queues are building up, providers are degraded, or a background component has stopped reporting.

As the two-year historical-data work increases the importance of asynchronous data readiness, the operator needs a single trusted place to answer questions such as:

- From which date to which date is historical data actually available for each market?
- Is the two-year backfill complete, partial, stalled, or degraded?
- Which application components are currently reporting?
- Which component is working on something right now?
- Which workers are stale or degraded?
- Are Binance REST, Binance WebSocket, Binance Public Data, PostgreSQL, and Telegram healthy?
- Are historical-analysis or notification queues building up?
- What warnings/errors happened recently and which component emitted them?
- Is a `future_event` problem consistent with a clock problem?
- Which safe runtime configuration/version is deployed?

## Product direction

The admin console is an application-owned **read-only operations control plane**.

```text
/admin
  ├── Overview
  ├── Data
  ├── Components
  ├── Jobs & Queues
  ├── Logs
  └── System
```

The first version observes and explains system state. It does not control infrastructure.

## Core architectural rule

The admin console must observe FreeCoinAlert through FreeCoinAlert-owned state and telemetry.

```text
application components
        ↓
heartbeats / canonical DB state / structured operational events
        ↓
protected admin APIs
        ↓
/admin
```

It must **not** become:

```text
/admin
  ↓
Docker socket
  ↓
inspect/control host containers
```

Do not mount `/var/run/docker.sock`, shell out to `docker logs`, execute arbitrary commands, or couple the admin contract to Docker Compose. This keeps the design portable to later orchestration environments such as ECS or Kubernetes and avoids giving the web/API process host-control privileges.

## Authorization

The admin console is private and server-authorized.

Introduce at least:

```text
user
admin
```

The server owns the role. Clients cannot promote themselves.

Expected behavior:

```text
anonymous → authentication failure
normal authenticated user → 403
admin → allowed
```

Admin promotion/revocation is initially an explicit operator action, not a public/self-service API.

All `/admin` pages are `noindex`/`nofollow` and must remain absent from public sitemap/marketing navigation.

## Admin overview

The overview must answer the primary question within a few seconds:

> Is FreeCoinAlert healthy right now, and if not, why?

Example information hierarchy:

```text
FreeCoinAlert Admin                         Updated 3s ago

Overall status
DEGRADED
SOLUSDT long-range historical coverage is still backfilling.
Core live alerts remain available.

Components        Data readiness        Backfill        Queues
6/6 healthy       4/5 ready             82.6%           1 running

Recent warnings/errors
12:20  candle-backfill    archive_checksum_failed
12:17  market-stream      stale_event
11:54  historical-worker analysis_attempts_exhausted
```

Overall status uses a small vocabulary such as:

```text
healthy
degraded
critical
```

The UI must explain the reason rather than showing a color/status alone.

## Data readiness

Data readiness must be based on canonical server/database coverage, not browser date arithmetic.

For every controlled market/timeframe expose useful information such as:

```text
symbol
exchange
market type
timeframe
available start
available end
target start
target end
coverage/completeness
backfill state/progress
latest closed candle/freshness
missing-range count or bounded summary
historical-analysis availability
```

Example:

```text
Symbol    Available history                 State
BTCUSDT   Jul 2024 → Aug 2026               Ready
ETHUSDT   Jul 2024 → Aug 2026               Ready
BNBUSDT   Jul 2024 → Aug 2026               Ready
SOLUSDT   Nov 2024 → Aug 2026               Backfilling · 82%
XRPUSDT   Jul 2024 → Aug 2026               Ready
```

A market drill-down can show target range, current contiguous coverage, completeness, gaps, latest candle freshness, and whether 30D/90D/6M/1Y/2Y historical-analysis ranges are currently usable.

## Runtime component registry

Do not infer worker liveness from Docker.

Each long-running process reports a small heartbeat into an application-owned runtime registry.

Minimum component set:

```text
API
market-stream
candle-backfill-worker
historical-analysis-worker
notification-worker
signal-telegram-dispatcher
telegram-updates (when enabled)
```

The registry should support safe information such as:

```text
component key
instance ID
started at
last heartbeat at
declared state
last success at
last error at
last error category
application version
git revision
small allow-listed component detail payload
```

Expected component states include:

```text
healthy
working
degraded
stale
not_reporting
disabled
```

Do not report `stopped` unless the application actually knows orchestration intentionally stopped the process.

Stale status is derived from heartbeat age using a deterministic threshold.

## Component details

Small component-specific detail is useful when safe.

Examples:

### Market stream

```text
websocket connected
last accepted event
stale-symbol count
recent future/stale/invalid event counts
```

### Candle backfill

```text
current symbol
current archive/work unit
coverage progress
last successful unit
last failure category
```

### Historical worker

```text
current run ID
last completed run
last failure category
```

Canonical data such as candle coverage remains in its canonical tables and should not be duplicated as arbitrary heartbeat JSON.

## External dependency health

Application components and dependencies are different concepts and must be displayed separately.

Dependencies can include:

```text
PostgreSQL
Binance REST
Binance WebSocket
Binance Public Data
Telegram API (when configured)
```

Useful safe diagnostics include:

### PostgreSQL
- availability
- bounded query latency
- database UTC

### Binance REST
- current shared rate-budget state
- recent request-weight state where available
- active 429/backoff state
- active 418 blocked state
- recent provider failure category

### Binance WebSocket
- connected/reconnecting/degraded state
- last accepted message/event time

### Binance Public Data
- recent archive success/failure state

### Telegram
- enabled/disabled
- recent successful provider request or recent failure category where available

Admin reads existing state; it should not generate frequent external provider probes that become a new source of load/rate limiting.

## Jobs and queues

The console must make hidden buildup visible.

### Historical analysis

Show bounded summaries such as:

```text
queued
running
completed in recent window
failed in recent window
oldest queued age
recent jobs
```

### Notifications and signals

Show durable pending/retry/failure state from existing outboxes/queues.

### Backfill

Show current work unit, remaining/progress state, last success, and recent failure information.

Recent job tables should be bounded and paginated where needed.

## Structured operational logs

The admin console needs recent operational events, but the API must not read Docker logs.

Keep normal stdout/stderr as the primary runtime log output. Add a bounded structured admin log feed for operationally useful events.

Conceptual fields:

```text
id
occurred_at
component
instance_id
level
category
correlation_id
message
details
```

Expected filters:

```text
component
severity
category
correlation ID
time range
bounded text search
```

The log feed is intentionally not a full debug/trace store.

Do not persist every candle, every websocket message, every HTTP 200, or every heartbeat.

Useful event classes include:

```text
component lifecycle
job lifecycle
provider degradation/recovery
retry/backoff
state transition
WARN
ERROR
important INFO operational transitions
```

## Log retention and safety

Operational logs stored for the admin console must be bounded and automatically cleaned up. A short operational retention window such as approximately seven days is appropriate for the initial PostgreSQL-backed implementation, with the exact policy locked during technical design.

Never persist/display secrets such as:

```text
Telegram bot token
session cookie
password/password hash
CSRF token
Authorization header
DB password/full DATABASE_URL
provider credentials
confidential request payloads
```

Structured detail is allow-listed rather than arbitrary object serialization.

Cap message/detail size and nesting.

Failure of the admin log sink must not crash the business component attempting to emit a log.

The storage/API boundary should remain replaceable by a dedicated log backend later without redesigning the admin UI contract.

## Clock diagnostics

Because market-event future/stale validation depends on time, expose a small clock diagnostic:

```text
application UTC
database UTC
difference
recent future-event offset summary where available
```

This does not replace host/NTP monitoring. It simply makes obvious application/database-time anomalies visible from the console.

## Safe system information

Expose only allow-listed diagnostics such as:

```text
environment name
application version
git revision
API/process uptime where meaningful
current Alembic/database revision where practical
server UTC
configured candle backfill target days
historical-analysis maximum range
market future-event tolerance
other explicitly reviewed non-secret operational limits
```

Never expose unrestricted environment variables or raw settings objects.

## Admin API direction

Keep `/health` small and stable for infrastructure probes.

Use a protected admin namespace, conceptually:

```text
GET /admin/overview
GET /admin/components
GET /admin/components/{component}
GET /admin/data-readiness
GET /admin/data-readiness/{symbol}
GET /admin/jobs
GET /admin/dependencies
GET /admin/logs
GET /admin/system
```

The exact endpoint split and schemas are owned by technical design.

All initial endpoints are read-only.

## Refresh behavior

The admin UI may use bounded polling rather than introducing a new realtime transport solely for this story.

Suggested behavior:

```text
overview/components/queues: about every 5s
data readiness: about every 15s
logs: about every 3–5s only while live mode is enabled
```

Exact cadence is technical-design scope.

Reduce or pause polling when the tab is hidden where practical.

Always display the last successful refresh time.

If refresh fails, visibly mark data as stale. Old green statuses must never continue looking current without a freshness warning.

## Visual direction

This is an operations interface, not a marketing dashboard.

Prefer dense, scan-friendly information:

```text
● Healthy
◐ Working
● Degraded
● Critical
○ Disabled
○ Not reporting
```

Status meaning must not depend on color alone.

Healthy information should remain visually quiet while abnormal states attract attention.

The interface is desktop-first but must remain usable on tablet/mobile with accessible tables or stacked representations.

## Read-only MVP boundary

US-0016 intentionally does **not** include:

```text
restart service
stop service
edit environment variables
run migrations
delete user
delete candles
force-close analyses
manual SQL
arbitrary shell commands
Docker/container controls
```

Future administrative actions must be designed individually with server authorization, CSRF protection where applicable, confirmation, auditability, idempotency, and explicit safety semantics.

## Security invariants

- Admin authorization is enforced server-side.
- Normal users receive no operational admin payloads.
- Client-side hiding is not authorization.
- No Docker socket/host-control privilege is granted to the application.
- No unrestricted configuration/environment dumps.
- No secrets in operational logs/API responses.
- Admin routes are private/noindex and absent from public sitemap/marketing navigation.
- Admin APIs are bounded to prevent accidental expensive scans or unbounded log responses.

## Acceptance criteria

- Only administrators can access `/admin` pages and `/admin` APIs.
- Anonymous and ordinary authenticated users cannot retrieve admin operational data.
- Current runtime components and last heartbeats are visible.
- Healthy, working, degraded, stale, not-reporting, and intentionally disabled states can be represented truthfully.
- Per-symbol historical-data available start/end and target range are visible.
- Backfill progress and readiness are visible.
- Candle freshness/gap state is visible without scanning millions of rows in Python.
- Historical-analysis queue condition is visible.
- Notification/signal delivery queue condition is visible.
- Binance REST/WS/public-data state is visible from existing application telemetry.
- Telegram/PostgreSQL dependency state is visible where applicable.
- Recent structured operational logs can be filtered with bounded pagination.
- Operational log retention is bounded and automatically cleaned up.
- Secrets and confidential request/session data are excluded from admin logs/responses.
- Overall admin state explains why the system is degraded/critical.
- Failed admin refresh visibly marks displayed data stale.
- `/health` remains a small infrastructure health probe.
- Admin panel is read-only in this story.
- No Docker socket/container control is introduced.
- No real provider calls are required by E2E coverage.

## Implementation issues

1. #171 — `[AUTH] Add administrator role and protected admin boundary`
2. #172 — `[OBSERVABILITY] Add runtime component heartbeat and health registry`
3. #173 — `[ADMIN] Expose data readiness, provider health, jobs and queue diagnostics`
4. #174 — `[OBSERVABILITY] Add bounded structured component log feed`
5. #175 — `[WEB] Build the administrator operations console`
6. #176 — `[E2E] Cover administrator authorization and degraded-system observability`

Recommended order:

```text
#171
  ↓
#172
  ↓
#173 ─┐
      ├→ #175 → #176
#174 ─┘
```

#173 and #174 may proceed mostly in parallel after the administrator authorization boundary exists and after any required runtime-registry dependencies are available.

## Workflow

Each implementation issue requires an approved technical-solution comment before implementation.

Do not merge the story PR automatically. Do not implement child issues from this story document alone.