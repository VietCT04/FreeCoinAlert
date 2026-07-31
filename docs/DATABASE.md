# Database

## Purpose and Global Conventions

PostgreSQL is the durable source of truth. Tables use UUID primary keys unless a market state has a natural key; timestamps are UTC `TIMESTAMP WITH TIME ZONE`; amounts/prices are `NUMERIC(38,18)`; history is immutable where stated. Alembic manages the ordered schema chain. Exact constraints below are authoritative; runtime domain behavior is linked rather than duplicated.

## Schema Overview

| Domain | Tables | Form |
| --- | --- | --- |
| Identity | `users`, `auth_sessions` | mutable account/session state |
| Telegram | `telegram_connections`, `telegram_link_tokens`, `telegram_processed_updates` | connection state + idempotency |
| Delivery | `notification_outbox` | durable work lifecycle |
| Markets | `supported_markets`, `market_symbol_states` | catalogue + latest live snapshot |
| Candles | `market_candles`, `candle_symbol_states`, `candle_sync_runs` | immutable/revisioned candles + operations |
| Alerts | `price_alerts`, `alert_events` | mutable alert + immutable trigger |
| Signals | `signal_presets`, `signal_subscriptions`, `signal_evaluation_states`, `signal_events`, `signal_event_invalidations` | versioned definitions, user intent, state, immutable history |

## Authentication Domain

`users`: UUID `id`, display and normalized email, Argon2id `password_hash`, `created_at`, `updated_at`; normalized email is unique. `auth_sessions`: UUID `id`, `user_id` CASCADE, unique binary `token_hash`, CSRF token, created/expiry/revocation timestamps; expiry must follow creation and revocation cannot predate creation. User and expiry indexes support principal lookup/cleanup. Sessions are written by auth routes and revoked at sign-out.

## Telegram Domain

`telegram_connections` is one row per user (user FK CASCADE and unique), with unique Telegram user/chat IDs, username, persisted status (`connected`, `degraded`, `disconnected`), connection/verification/degraded/disconnection timestamps and safe reason. `linking` is an API-derived state when a user has an active token; it is not a database status. `telegram_link_tokens` stores a unique hashed short-lived link value and its user FK CASCADE, expiry, consumption, and revocation timestamps; it has no connection FK. Its partial unique user index permits one unconsumed, unrevoked token per user. `telegram_processed_updates` keys accepted provider update IDs for idempotency and retention cleanup. Link creation, update poller, and disconnect process write these rows. See [TELEGRAM.md](TELEGRAM.md).

## Notification Domain

`notification_outbox` is UUID-keyed durable work for a user and Telegram connection. It stores kind, idempotency key, payload snapshot, status (`pending`, `processing`, `retry_wait`, `sent`, `failed`), attempts, scheduling/claim/sent timestamps and safe failure code. User/connection FKs restrict deletion; unique user/kind/idempotency identity prevents replayed test notification work. Worker claim indexes support due work and recovery. Notification creation is transactional with price-alert trigger events.

## Supported-Market and Live-State Domain

`supported_markets` stores the controlled `(exchange, market_type, symbol)` catalogue uniquely, base/quote asset, provider status, exact min/max/tick rules, metadata/freshness timestamps and status reason. `market_symbol_states` has one PK/FK row per supported market with status (`starting`, `live`, `stale`, `disconnected`, `error`), last provider event identity/time, exact price, reconnect flag, reason and update time. Nonnegative provider IDs and finite positive prices are constrained. Catalogue sync and market stream write these tables.

## Candle Domain

`market_candles` is revisioned canonical history: UUID, market FK CASCADE, `1m`/`1h`/`4h` timeframe, UTC window, source kind, status (`complete`, `incomplete`, `invalid`, `superseded`), revision/current flag, optional predecessor, source counts/fingerprint, OHLCV/trade/provider fields, receipt and creation times. Constraints enforce duration/boundaries, revision chain, source shape/count, finite complete values and current/superseded relation. `(supported_market_id,timeframe,open_time,revision)` is unique; a partial unique current-row index and strategy/timeframe-read indexes support canonical lookups and evaluation.

`candle_symbol_states` is one FK-keyed current operational row with candle freshness timestamps, status (`starting`, `live`, `stale`, `gapped`, `error`), nonnegative unresolved-gap count and reason. `candle_sync_runs` records bounded bootstrap, reconciliation, recent reconciliation, or retention cleanup with requested range, current market, row counts, lifecycle (`running`, `succeeded`, `failed`, `cancelled`) and failure code. Candle ingestion, aggregation, and maintenance write these rows. See [MARKET_DATA.md](MARKET_DATA.md).

## One-Time Price-Alert Domain

`price_alerts` is UUID-keyed mutable user intent: user FK CASCADE, market and Telegram-connection FKs RESTRICT, `price_cross` type, direction, exact target/tick snapshot, lifecycle (`active`, `triggered`, `disabled`, `deleted`, `failed`), status reason, idempotency key, latest relation/price/provider state, and creation/update/trigger/disable/delete/failure timestamps. Lifecycle checks require the matching transition timestamp, including `deleted_at` for `deleted`. Unique `(user_id,idempotency_key)` supports safe create replay; owner/status and active-market indexes support UI and stream evaluation.

`alert_events` is immutable UUID-keyed price-cross history. It references alert, user, Telegram connection, captures a unique provider trigger identity, market/asset/direction/target/price snapshots, provider and observation timing, and reconnect context. Checks constrain event type/direction/identity/provider ID/finite values; unique alert/event identities prevent duplicate notifications. It is inserted with the matching outbox row. See [ALERTS.md](ALERTS.md).

## Preset and Signal Domain

`signal_presets` is immutable-in-meaning versioned catalogue data: code/version unique, presentation, strategy (`price_sma_cross` or `rsi_threshold_cross`), `1h`/`4h`, direction, period/threshold/close input, status (`active`, `superseded`, `disabled`), configuration hash unique, and lifecycle timestamps. Checks restrict it to SMA 200 and RSI 14 threshold 70/30 definitions.

`signal_subscriptions` stores user intent for a market and preset, with `active`/`disabled` status/reason and activation/disable times. FKs are user CASCADE and market/preset RESTRICT; `(user_id,supported_market_id,signal_preset_id)` is unique. User-list and active-preset indexes support subscription management.

`signal_evaluation_states` has a unique market/preset pair, status (`warming`, `ready`, `stale`, `error`, `disabled`), safe reason, last candle/revision/open time/relation and values, calculation-state version `1`, JSON calculation state, and timestamps. It is mutable evaluator state; market FK CASCADE and preset/candle FKs RESTRICT. Its status/update index supports maintenance.

`signal_events` is global immutable history, not per-user copies. It contains an identity-generated stream sequence (unique), market/preset/trigger-candle FKs RESTRICT, unique trigger identity and occurrence tuple, full market/preset/calculation/candle/value snapshots, backfill flag and occurrence/creation timestamps. Occurred, market/preset/occurred, and trigger-candle indexes support retrieval/rebuild. `signal_event_invalidations` records at most one immutable invalidation per event, with reason (`candle_corrected`, `preset_disabled`, `calculation_invariant`) and optional replacement candle/revision; its FKs restrict deletion and an event index supports joins. See [STRATEGIES.md](STRATEGIES.md) and [ALERTS.md](ALERTS.md).

## Cross-Domain Transaction Boundaries

Registration/login commit user/session together. Price-alert evaluation inserts event/outbox and transitions the alert atomically. Signal evaluation locks/updates its market-preset state and inserts a deduplicated signal event atomically. Telegram sending changes only outbox delivery state after the occurrence transaction.

## Retention and Cleanup

Canonical candle retention defaults to 180 days; processed Telegram updates default to 30 days; signal-event retention configuration defaults to 365 days but no automatic signal-event deletion process is implemented. Price events, alert records, and account-deletion retention remain governed by their FKs and operational policy.

## Migration Inventory

`20260728_0001` users/auth sessions; `20260730_0002` Telegram persistence; `0003` notification outbox; `0004` supported market catalogue; `0005` price alerts/events; `0006` live market state; `0007` price-alert notification kind; `0008` canonical candles; `0009` candle operational state; `0010` signal presets/subscriptions; `20260731_0011` signal evaluation/events/invalidations. The chain head is `20260731_0011`.

## Backup, Deletion, and Unresolved Storage Concerns

Production backup, restore testing, account deletion, and production migration rollout have no implemented operational policy. These are unresolved deployment risks, not claims of existing behavior.

## Verification Status

Schema contents were read from the SQLAlchemy registry and Alembic chain. No migration, database connection, or schema verification command was run.
