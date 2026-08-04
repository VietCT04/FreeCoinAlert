# Observability

## Purpose and Current Scope

FreeCoinAlert currently provides structured application logs and persisted operational state. It has no metrics exporter, dashboard, tracer, alerting rules, request IDs, or SLO monitoring.

## Health Endpoint and Its Limits

`GET /health` returns API process liveness (`status: ok`, service name) only. It does not check PostgreSQL, market freshness, candle continuity, alert evaluation, Telegram configuration, or notification delivery.

## Local Startup and Status Signals

The local wrapper does not add metrics, tracing, or a readiness endpoint. `pnpm dev:all` combines Compose `--wait` with JSON `ps --all` inspection: one-shot initialization services require exit code 0, database/API/web require Compose health, and the market stream plus enabled optional workers require a running state. `pnpm dev:status` exposes the same normalized `healthy`, `running`, `completed`, `starting`, `disabled`, `unavailable`, `failed`, and `stopped` states without requiring ports to be free. The readiness banner is printed only after required enabled services satisfy their state rules; startup failures remain concise and point to status and log commands.

The wrapper's profile selection is derived from validated local configuration and `docker compose config --profiles`. It reports Telegram as `disabled` when `LOCAL_ENABLE_TELEGRAM=false` and reports historical analysis as `unavailable` when that Compose profile is absent. It does not persist status, emit application log events, contact providers during preflight, or reinterpret the API's liveness response as dependency readiness.

## Persistent Operational State

`market_symbol_states` holds the latest accepted market-stream state; `candle_symbol_states` holds candle freshness/quality state; `candle_sync_runs` records bounded maintenance progress; `historical_analysis_runs` records owner-scoped historical-analysis request snapshots, lifecycle, progress, cancellation, attempts, and safe failure categories; `historical_analysis_datasets` records bounded canonical coverage, fingerprint, preparation, and stale state; `historical_analysis_dataset_candles` records immutable full-value candle snapshots; `historical_analysis_reports` records immutable owner-scoped result snapshots and summary metrics; `historical_analysis_trades` and `historical_analysis_equity_points` record immutable engine series; signal evaluation state records warming, ready, stale, or disabled calculation state; `signal_subscription_state_events` records immutable occurrence-time subscription and Telegram-preference state; `signal_feed_stream_events` records the bounded durable SSE cursor log; `signal_telegram_dispatches` records occurrence fan-out claims, cursors, counts, retries, skips, expiry, and failure; notification outbox rows record delivery processing. See [DATABASE.md](DATABASE.md) for schema and constraints.

## Structured Log Events by Subsystem

| Subsystem | Events / categories emitted |
| --- | --- |
| Auth | Authentication and origin/rate-limit failures through safe HTTP error handling. |
| Market catalog | Synchronization success/failure and provider failure category. |
| Market stream | reconnecting, queue backpressure, singleton-not-acquired, malformed/rejected input, and state updates. |
| Candles | reconciliation completed/failed/skipped and candle quality outcomes. |
| Price alerts | evaluator initialization, trigger, duplicate suppression, and safe evaluation failure. |
| Signal evaluator and subscriptions | `signal.evaluation.data_stale`, `insufficient_history`, `initialized`, `succeeded`, `signal.event.created`, `duplicate_suppressed`, subscription lifecycle outcomes, and Telegram-delivery preference changes. |
| Signal Telegram dispatcher | `signal.telegram.dispatch.claimed`, `page`, `completed`, `requeued`, and safe `failed` categories for database, expiry, invalidation, historical skip, destination skip, and attempt exhaustion. |
| Historical analysis API | Safe `historical.analysis.created`, `create_replayed`, `creation_rejected`, and `cancel_requested` lifecycle events; no candle payload, provider detail, report body, or user identifier is logged. |
| Historical analysis dataset | `historical.dataset.prepared`, `replayed`, `rejected`, and `stale` events with run/dataset/market/preset IDs, timeframe, counts, and safe failure category only; candle payloads, user IDs, SQL errors, and provider details are not logged. |
| Historical analysis engine | No logs, metrics, persistence, or provider events; the pure engine returns typed outcomes and a deterministic result fingerprint to its caller. |
| Historical analysis worker | `historical.analysis.claimed`, `progress`, `requeued`, `succeeded`, `failed`, `cancelled`, and `cleanup_completed`; only run/report/dataset IDs, versions, counts, durations, attempt counts, stages, and safe failure categories are allowed. |
| Signal feed | `signal.feed.history_read`, `history_latency`, `listener_connected`, `listener_reconnecting`, `listener_failed`, `connection_opened`, `connection_closed`, `connection_rejected`, `replay_completed`, `reset_required`, `backpressure`, `auth_expired`, `event_published`, `event_sent`, and stream cleanup categories. |
| Telegram | update received/duplicate, link succeeded/rejected, confirmation sent/failed, polling failure. |
| Notification worker | claim, strict preset-payload rejection, send, retry, terminal failure, recovery, outcome-unknown, and provider outcome categories. |

The exact field set is implementation detail; logs use IDs and safe categories rather than credentials or provider payloads. The browser price-alert, preset-signal, Telegram, signal, and historical-analysis panels do not log event/report payloads, subscription or run IDs, cursors, authentication values, CSRF values, Telegram readiness, fingerprints, trades, equity, destination identifiers, or sound state; connection status, card presentation, report presentation, and sound activation are visual client state only. Preference, usage-summary, and historical-analysis controls use safe announcements without logging provider details. A successful mutation toast or a `sent` test-notification result does not imply device receipt, a signal notification job, a Telegram provider request for another feature, or a live occurrence was created.

## Status and Freshness Semantics

Historical-analysis `queued`, `running`, `succeeded`, `failed`, and `cancelled` states describe request/lifecycle persistence. `succeeded` means the worker atomically published the immutable report and series; the other states do not indicate report availability or provider work. Dataset `ready` means bounded canonical snapshots were prepared, `failed` means preparation recorded a safe coverage outcome, and `stale` means a later current-candle check found a source mismatch. A pure engine `success` result means a hypothetical simulation completed for immutable inputs; the worker's publication transition is the report-availability boundary. Dataset and worker logs never contain candle payloads, user IDs, provider details, raw SQL errors, trade/equity series, or report bodies.

Market data accepts aggregate trades only inside the configured age/future tolerance. Stream disconnection or stale market state pauses price-alert evaluation. Candle `stale`, `gapped`, or `error` state prevents preset signal creation. A signal dispatch `pending`/`processing`/`retry_wait` state represents database fan-out work; `completed` means all bounded eligible-state pages were processed, including any recorded destination skips; `skipped` means no delivery work was attempted for backfill, invalidation, or expiry; `failed` means fan-out recovery reached its attempt limit. Notification `queued`, `sending`, `retrying`, `sent`, and `failed` represent provider processing, while `sent` means Telegram acceptance rather than device receipt. `failed` also covers malformed preset payloads, revoked consent, invalidated occurrences, unavailable destinations, missing configuration, and provider failures. Connection `degraded` is a safe availability state. A signal Telegram-delivery preference is user intent; its readiness is dynamic and does not indicate a queued or sent notification. Detailed lifecycle meaning is in [MARKET_DATA.md](MARKET_DATA.md), [ALERTS.md](ALERTS.md), and [TELEGRAM.md](TELEGRAM.md).

## Counters and Measurements Actually Emitted

The implementation records counters and timestamps in operational rows (latest event identity/time, candle state, maintenance progress, evaluator state, dispatch attempt/cursor/count/claim fields, outbox attempt/claim fields, and provider message IDs). Signal-feed logs include active/rejected connections, listener state/reconnects, published and consumed sequences, live/replay counts, queue depth/backpressure resets, session-expiry closures, and history latency fields where available. Dispatcher logs include safe event identifiers, page counts, stale claims, terminal categories, and attempt exhaustion without recipient or message data. It does not expose Prometheus metrics, aggregate counters, latency histograms, dashboards, or alert thresholds.

## Sensitive-Data Redaction

Do not log session tokens, password values/hashes, raw Telegram link tokens, bot tokens, chat IDs, database URLs, webhook secrets, or complete provider payloads. User-facing failures use stable safe categories.

## Incident Indicators

Investigate a failed `pnpm dev:all` readiness attempt, failed initialization or health state in `pnpm dev:status`, a missing enabled worker, missing/old market event, disconnected stream, stale/gapped/error candle state, skipped or failed reconciliation, warming/stale evaluator state, failed or stale historical-analysis datasets, queued/running/failed/requeued historical-analysis work, report publication failures, cleanup failures, signal-feed listener failure/reconnects, reset/backpressure growth, session-expiry closures, pending/retry-wait/failed signal dispatch growth, queued/retrying/failed outbox growth, degraded/disconnected Telegram connection, or 429/418/provider categories in logs. These are operator indicators, not automated incident alerts.

## Troubleshooting Links

Use [OPERATIONS.md](OPERATIONS.md) for recovery actions, [MARKET_DATA.md](MARKET_DATA.md) for data-quality semantics, and [TELEGRAM.md](TELEGRAM.md) for provider delivery behavior.

## Missing Observability and Unresolved Gaps

Cross-process metrics, dashboards, tracing, production readiness/dependency health, automated alerting, and verified alert-delivery monitoring are absent. These risks are tracked in [CONCERNS.md](CONCERNS.md).

## Verification Status

This inventory is based on static code inspection plus a maintainer-requested local startup/status pass. Database, API/web health, migration, market initialization, market-stream startup, and historical-worker states were exercised; signal-feed, Telegram, browser, maintenance, reset, and production observability remain unverified.
