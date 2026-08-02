# Observability

## Purpose and Current Scope

FreeCoinAlert currently provides structured application logs and persisted operational state. It has no metrics exporter, dashboard, tracer, alerting rules, request IDs, or SLO monitoring.

## Health Endpoint and Its Limits

`GET /health` returns API process liveness (`status: ok`, service name) only. It does not check PostgreSQL, market freshness, candle continuity, alert evaluation, Telegram configuration, or notification delivery.

## Persistent Operational State

`market_symbol_states` holds the latest accepted market-stream state; `candle_symbol_states` holds candle freshness/quality state; `candle_sync_runs` records bounded maintenance progress; signal evaluation state records warming, ready, stale, or disabled calculation state; `signal_feed_stream_events` records the bounded durable SSE cursor log; notification outbox rows record delivery processing. See [DATABASE.md](DATABASE.md) for schema and constraints.

## Structured Log Events by Subsystem

| Subsystem | Events / categories emitted |
| --- | --- |
| Auth | Authentication and origin/rate-limit failures through safe HTTP error handling. |
| Market catalog | Synchronization success/failure and provider failure category. |
| Market stream | reconnecting, queue backpressure, singleton-not-acquired, malformed/rejected input, and state updates. |
| Candles | reconciliation completed/failed/skipped and candle quality outcomes. |
| Price alerts | evaluator initialization, trigger, duplicate suppression, and safe evaluation failure. |
| Signal evaluator | `signal.evaluation.data_stale`, `insufficient_history`, `initialized`, `succeeded`, `signal.event.created`, and `duplicate_suppressed`. |
| Signal feed | `signal.feed.history_read`, `history_latency`, `listener_connected`, `listener_reconnecting`, `listener_failed`, `connection_opened`, `connection_closed`, `connection_rejected`, `replay_completed`, `reset_required`, `backpressure`, `auth_expired`, `event_published`, `event_sent`, and stream cleanup categories. |
| Telegram | update received/duplicate, link succeeded/rejected, confirmation sent/failed, polling failure. |
| Notification worker | claim, send, retry, terminal failure, recovery, and provider outcome categories. |

The exact field set is implementation detail; logs use IDs and safe categories rather than credentials or provider payloads.

## Status and Freshness Semantics

Market data accepts aggregate trades only inside the configured age/future tolerance. Stream disconnection or stale market state pauses price-alert evaluation. Candle `stale`, `gapped`, or `error` state prevents preset signal creation. Notification `queued`, `sending`, `retrying`, `sent`, and `failed` represent platform processing, while `sent` means Telegram acceptance rather than device receipt. Connection `degraded` is a safe availability state. Detailed lifecycle meaning is in [MARKET_DATA.md](MARKET_DATA.md), [ALERTS.md](ALERTS.md), and [TELEGRAM.md](TELEGRAM.md).

## Counters and Measurements Actually Emitted

The implementation records counters and timestamps in operational rows (latest event identity/time, candle state, maintenance progress, evaluator state, attempt counts, claim times, and provider message IDs). Signal-feed logs include active/rejected connections, listener state/reconnects, published and consumed sequences, live/replay counts, queue depth/backpressure resets, session-expiry closures, and history latency fields where available. It does not expose Prometheus metrics, aggregate counters, latency histograms, dashboards, or alert thresholds.

## Sensitive-Data Redaction

Do not log session tokens, password values/hashes, raw Telegram link tokens, bot tokens, chat IDs, database URLs, webhook secrets, or complete provider payloads. User-facing failures use stable safe categories.

## Incident Indicators

Investigate a missing/old market event, disconnected stream, stale/gapped/error candle state, skipped or failed reconciliation, warming/stale evaluator state, signal-feed listener failure/reconnects, reset/backpressure growth, session-expiry closures, queued/retrying/failed outbox growth, degraded/disconnected Telegram connection, or 429/418/provider categories in logs. These are operator indicators, not automated incident alerts.

## Troubleshooting Links

Use [OPERATIONS.md](OPERATIONS.md) for recovery actions, [MARKET_DATA.md](MARKET_DATA.md) for data-quality semantics, and [TELEGRAM.md](TELEGRAM.md) for provider delivery behavior.

## Missing Observability and Unresolved Gaps

Cross-process metrics, dashboards, tracing, production readiness/dependency health, automated alerting, and verified alert-delivery monitoring are absent. These risks are tracked in [CONCERNS.md](CONCERNS.md).

## Verification Status

This inventory is based on static code inspection. No logs, health endpoint, processes, or operational tables were exercised.
