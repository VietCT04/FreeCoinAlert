# Observability

## Purpose

This document defines logs, metrics, health checks, freshness signals, alert-delivery monitoring, and incident-oriented diagnostics.

## Observability Principles

- A running HTTP process is not enough to call the system healthy.
- Monitor user outcomes as well as process availability.
- Use structured logs with stable event names and correlation identifiers.
- Avoid logging every market tick in production.
- Do not log secrets or unnecessary personal data.
- Distinguish temporary provider degradation from permanent application failure.

## Health Dimensions

### API Health

`GET /health` is API liveness/process health only. It confirms that the FastAPI process can serve the endpoint, without checking dependencies.

It is not readiness for PostgreSQL, market-data ingestion, alert evaluation, Telegram delivery, or any future worker. It must not claim that alerts are operating correctly when market data or notification processing is stale.

### Local Compose Health Checks

The local `web` container health check confirms that the Next.js development server responds on port `3000`. The `api` check calls its process-health endpoint on port `8000`. The `db` check uses `pg_isready` to confirm that PostgreSQL accepts connections. These checks are local container liveness signals only; they do not prove application database connectivity, migrations, end-to-end product readiness, backups, or production readiness.

### Market-Data Health

Track:

- Binance WebSocket connection state
- Time of last event received
- Time of last closed candle stored per supported symbol
- Reconnect count
- Subscription count
- Known candle gaps

Issue #48 introduces no worker metrics or health endpoint. Future market-data observability must distinguish complete, incomplete, invalid, and superseded candle revisions; report the latest current complete `1m` candle, bounded missing ranges, derived-window source counts, and revision replacements without recording raw provider payloads.
- Reconciliation backlog and failures
- REST rate-limit responses

Define a documented freshness threshold per stream type.

### Alert-Engine Health

Track:

- Events evaluated
- Evaluation latency
- Rules skipped because data was incomplete or stale
- Trigger count
- Duplicate events prevented
- Evaluation failures by rule type
- Active alert count by market and timeframe

### Notification Health

Track:

- Pending, claimed, sent, retrying, and permanently failed jobs
- Oldest pending job age
- Delivery latency
- Telegram rate-limit responses
- Bot-blocked and unavailable-chat failures
- Duplicate deliveries prevented

### Database Health

Track:

- Connection availability
- Query latency on critical paths
- Connection-pool use
- Storage growth
- Migration state
- Candle write failures
- Outbox backlog
- Partition or disk capacity when relevant

### Future Historical-Job Health

Track separately from live processing:

- Queued and running jobs
- Job duration
- Resource use
- Failure category
- Data-coverage failures
- Whether live alert service levels are affected

## Structured Logging

### Supported-Market Catalog

The explicit catalog-sync command emits safe structured events `market.catalog.sync_started`,
`market.catalog.sync_succeeded`, `market.catalog.sync_failed`, and `market.catalog.symbol_unavailable`.
They may include exchange, market type, symbol, stable provider-status category, row count, retry delay,
and duration. They must never include raw `/exchangeInfo` payloads, unrestricted exception text, headers,
credentials, cookies, Telegram data, or provider secrets.

Recommended fields include:

- Timestamp in UTC
- Severity
- Service or process
- Environment
- Event name
- Request, alert, candle, job, or correlation ID
- Exchange, market, symbol, and timeframe when relevant
- Safe error category
- Duration

Do not log:

- Passwords
- Sessions or access tokens
- Telegram bot token or webhook secret
- Raw one-time link tokens
- Database credentials
- Full chat IDs unless strictly required and protected

Authentication session rejection and logout events use the safe event names
`auth.session.rejected` and `auth.logout.success`. Successful logout events may include
internal user and session UUIDs for audit correlation. They must never include raw
cookies, session tokens, CSRF tokens, request headers, passwords, or authentication
request bodies.

## Audit Events

Sensitive user actions should be auditable, including:

- Telegram connected or disconnected
- Alert created, updated, paused, resumed, or deleted
- Template version changed for a subscription
- Administrative symbol or template changes
- Account-security changes

Audit data must have a retention and access policy before production.

## Alerts for Operators

Operational alerts should eventually cover:

- WebSocket disconnected beyond threshold
- Market data stale
- Candle gaps unresolved
- Reconciliation repeatedly failing
- Binance REST 429 or 418 responses
- Notification backlog age above threshold
- Telegram delivery failure spike
- Database unavailable
- Disk or storage near capacity
- Error-rate spike

Thresholds must be based on measured behavior and user impact.

## Dashboards

A minimal operational dashboard should answer:

- Is live market data current?
- Are all supported symbols receiving closed candles?
- Are alerts being evaluated?
- Are notification jobs being delivered?
- Is a backlog growing?
- Are external providers rate limiting or failing?
- Are database and storage resources healthy?

## Error Tracking

An error-tracking service may be used, but the application should not depend on a specific provider.

Group errors by safe category and include enough context to reproduce the failure without exposing secrets.

## Data-Quality Visibility

Maintain explicit states for:

- Complete
- Missing ranges detected
- Repair in progress
- Repair failed
- Unsupported or disabled

Do not hide data gaps only inside logs. Persistent gaps should appear in operational status and `CONCERNS.md` when they represent ongoing risk.

## Testing and Verification

Verify that:

- Health endpoints report dependency failure accurately.
- Stale market data is distinguishable from a healthy socket process.
- Metrics do not contain unbounded user-controlled labels.
- Logs redact secrets.
- Notification backlog and retry states are visible.
- Duplicate-prevention counters behave as expected.

## Pending Decisions

## Issue #22 Notification Events

The worker emits structured `notification.queued`, `notification.claimed`, `notification.sent`,
`notification.retry_scheduled`, `notification.failed`, `notification.outcome_unknown`, and
`telegram.connection.degraded` events. Safe fields include internal notification, user, and
connection IDs, attempt count, and stable failure category. Logs exclude tokens, raw Telegram
identifiers, message text, provider URLs, and provider responses.

- Logging and metrics libraries.
- Error-tracking provider.
- Metrics storage and dashboard provider.
- Freshness and backlog thresholds.
- On-call or notification destination for operator alerts.
- Audit-log retention.

## Issue #21 Telegram Processor Events

The processor emits `telegram.update.received`, `telegram.update.duplicate`,
`telegram.link.succeeded`, `telegram.link.rejected`, `telegram.confirmation.sent`,
`telegram.confirmation.failed`, and `telegram.polling.failed`. Safe fields may include an update
ID and internal connection or user identifier after resolution. Events must not include raw links,
token hashes, full updates, full message text, bot tokens, or provider exception bodies.

## Issue #30 Price Alert API Events

The alert API emits `alert.price.created`, `alert.price.create_replayed`, `alert.price.creation_rejected`,
`alert.price.deleted`, and `alert.price.delete_rejected`. Safe fields may include internal alert/user UUIDs,
canonical symbol, direction, and stable result category. Do not log request bodies, idempotency keys, sessions,
CSRF tokens, Telegram identifiers, provider identifiers, or unrestricted persistence errors.
# Live-price stream signals

The market stream emits safe structured events for startup, connection, reconnection, disconnect, singleton rejection, accepted/invalid/stale/duplicate/out-of-order events, sequence jumps, pipeline backpressure, symbol live state, and symbol stale state. Fields are limited to exchange, market type, symbol, provider event ID, connection generation, queue depth, event age, reconnect attempt, and stable error categories. Raw provider payloads, full WebSocket URLs, user and alert data, and credentials are never logged.

Operational state records connection status, latest accepted event, state-write failures, catalog-refresh outcomes, and freshness. These are operational signals, not a current-price API or alert-delivery guarantee.

## Price-Alert Evaluation Signals

Issue #32 emits safe structured categories for initialization, relation change, old-event suppression, trigger
creation or duplicate suppression, invariant failure, market disablement, notification queueing, and registry
refresh success/failure. Metrics should track registry size, evaluation duration, relation changes, triggers,
duplicate suppression, disabled or failed alerts, queued jobs, delivery outcomes, refresh lag, and backpressure.
