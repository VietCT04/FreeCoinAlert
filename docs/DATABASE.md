# Database

## Purpose and Global Conventions

PostgreSQL is the durable source of truth. Tables generally use UUID primary keys. Exceptions include provider-owned or domain-natural identities such as `telegram_processed_updates.update_id` and supported-market-keyed operational state rows. Timestamps are UTC `TIMESTAMP WITH TIME ZONE`; amounts/prices are `NUMERIC(38,18)`; history is immutable where stated. Alembic manages the ordered schema chain. Exact constraints below are authoritative; runtime domain behavior is linked rather than duplicated.

## Schema Overview

| Domain | Tables | Form |
| --- | --- | --- |
| Identity | `users`, `auth_sessions` | mutable account/session state |
| Telegram | `telegram_connections`, `telegram_link_tokens`, `telegram_processed_updates` | connection state + idempotency |
| Delivery | `notification_outbox`, `signal_telegram_dispatches` | durable work lifecycle and occurrence fan-out state |
| Markets | `supported_markets`, `market_symbol_states` | catalogue + latest live snapshot |
| Candles | `market_candles`, `candle_symbol_states`, `candle_sync_runs` | immutable/revisioned candles + operations |
| Alerts | `price_alerts`, `alert_events` | mutable alert + immutable trigger |
| Signals | `signal_presets`, `signal_subscriptions`, `signal_subscription_state_events`, `signal_evaluation_states`, `signal_events`, `signal_event_invalidations`, `signal_feed_stream_events` | versioned definitions, user intent, occurrence-time subscription state, evaluation state, immutable history, durable feed cursor |
| Historical analysis | `historical_analysis_runs`, `historical_analysis_datasets`, `historical_analysis_dataset_candles` | owner-scoped request/lifecycle state plus immutable canonical candle snapshots |

## Authentication Domain

`users`: UUID `id`, display and normalized email, Argon2id `password_hash`, `created_at`, `updated_at`; normalized email is unique. `auth_sessions`: UUID `id`, `user_id` CASCADE, unique binary `token_hash`, CSRF token, created/expiry/revocation timestamps; expiry must follow creation and revocation cannot predate creation. User and expiry indexes support principal lookup/cleanup. Sessions are written by auth routes and revoked at sign-out.

## Telegram Domain

`telegram_connections` is one row per user (user FK CASCADE and unique), with unique Telegram user/chat IDs, username, persisted status (`connected`, `degraded`, `disconnected`), connection/verification/degraded/disconnection timestamps and safe reason. `linking` is an API-derived state when a user has an active token; it is not a database status. `telegram_link_tokens` stores a unique hashed short-lived link value and its user FK CASCADE, expiry, consumption, and revocation timestamps; it has no connection FK. Its partial unique user index permits one unconsumed, unrevoked token per user. `telegram_processed_updates` keys accepted provider update IDs for idempotency and retention cleanup. Link creation, update poller, and disconnect process write these rows. See [TELEGRAM.md](TELEGRAM.md).

## Notification Domain

`notification_outbox` is UUID-keyed durable work for a user and Telegram connection. It stores kind (`telegram_test`, `telegram_price_alert`, or `telegram_preset_signal`), idempotency key, payload snapshot, status (`pending`, `processing`, `retry_wait`, `sent`, `failed`), attempts, scheduling/claim/sent timestamps and safe failure code. Preset-signal rows require both `signal_event_id` and `signal_subscription_id`; existing kinds require both references to be null. Those references use `ON DELETE RESTRICT`. The user FK cascades deletion, while the Telegram-connection FK restricts deletion. The unique `(user_id, idempotency_key)` constraint remains global, and the partial unique `(user_id, signal_event_id) WHERE kind = 'telegram_preset_signal'` rule prevents duplicate logical preset-signal jobs. Worker claim indexes support due work and recovery. Notification creation is transactional with price-alert trigger events or a dispatcher page.

`signal_telegram_dispatches` is one UUID-keyed durable fan-out row per immutable `signal_events` row. `signal_event_id` is unique and `ON DELETE RESTRICT`; `status` is `pending`, `processing`, `retry_wait`, `completed`, `skipped`, or `failed`. It stores the bounded subscription cursor, notification/skipped counts, attempt/max-attempt values, availability and claim fields, terminal timestamps, safe failure code, and created/updated timestamps. Claim and stale-processing indexes support `FOR UPDATE SKIP LOCKED`, recovery, and bounded replay. Backfilled occurrences are inserted as `skipped` with `historical_backfill_not_delivered`; existing historical events receive no dispatch row during migration.

## Supported-Market and Live-State Domain

`supported_markets` stores the controlled `(exchange, market_type, symbol)` catalogue uniquely, base/quote asset, provider status, exact min/max/tick rules, metadata/freshness timestamps and status reason. `market_symbol_states` has one PK/FK row per supported market with status (`starting`, `live`, `stale`, `disconnected`, `error`), last provider event identity/time, exact price, connection-generation UUID, reason and update time. Nonnegative provider IDs and finite positive prices are constrained. Catalogue sync and market stream write these tables.

## Candle Domain

`market_candles` is revisioned canonical history: UUID, market FK CASCADE, `1m`/`1h`/`4h` timeframe, UTC window, source kind, status (`complete`, `incomplete`, `invalid`, `superseded`), revision/current flag, optional predecessor, source counts/fingerprint, OHLCV/trade/provider fields, receipt and creation times. Constraints enforce duration/boundaries, revision chain, source shape/count, finite complete values and current/superseded relation. `(supported_market_id,timeframe,open_time,revision)` is unique; a partial unique current-row index and strategy/timeframe-read indexes support canonical lookups and evaluation.

`candle_symbol_states` is one FK-keyed current operational row with candle freshness timestamps, status (`starting`, `live`, `stale`, `gapped`, `error`), nonnegative unresolved-gap count and reason. `candle_sync_runs` records bounded bootstrap, reconciliation, recent reconciliation, or retention cleanup with requested range, current market, row counts, lifecycle (`running`, `succeeded`, `failed`, `cancelled`) and failure code. Candle ingestion, aggregation, and maintenance write these rows. See [MARKET_DATA.md](MARKET_DATA.md).

## One-Time Price-Alert Domain

`price_alerts` is UUID-keyed mutable user intent: user FK CASCADE, market and Telegram-connection FKs RESTRICT, `price_cross` type, direction, exact target/tick snapshot, lifecycle (`active`, `triggered`, `disabled`, `deleted`, `failed`), status reason, idempotency key, latest relation/price/provider state, and creation/update/trigger/disable/delete/failure timestamps. Lifecycle checks require the matching transition timestamp, including `deleted_at` for `deleted`. Unique `(user_id,idempotency_key)` supports safe create replay; owner/status and active-market indexes support UI and stream evaluation.

`alert_events` is immutable UUID-keyed price-cross history. It references alert, user, Telegram connection, captures a unique provider trigger identity, market/asset/direction/target/price snapshots, provider and observation timing, and reconnect context. Checks constrain event type/direction/identity/provider ID/finite values; unique alert/event identities prevent duplicate notifications. It is inserted with the matching outbox row. See [ALERTS.md](ALERTS.md).

## Preset and Signal Domain

`signal_presets` is immutable-in-meaning versioned catalogue data: code/version unique, presentation, strategy (`price_sma_cross` or `rsi_threshold_cross`), `1h`/`4h`, direction, period/threshold/close input, status (`active`, `superseded`, `disabled`), configuration hash unique, and lifecycle timestamps. Checks restrict it to SMA 200 and RSI 14 threshold 70/30 definitions.

`signal_subscriptions` stores user intent for a market and preset, with `active`/`disabled` status/reason and activation/disable times. `telegram_delivery_enabled` is `BOOLEAN NOT NULL DEFAULT FALSE`; `telegram_delivery_changed_at` records the last explicit preference change and is null when the current subscription interval has not enabled delivery. New subscriptions and reactivations reset the preference to false; disabling a subscription also resets it. FKs are user CASCADE and market/preset RESTRICT; `(user_id,supported_market_id,signal_preset_id)` is unique. User-list and active-preset indexes support subscription management.

`signal_subscription_state_events` is immutable occurrence-time history for later signal fan-out. It has identity `sequence BIGINT` primary key, subscription/user/market/preset references, `subscription_status` (`active` or `disabled`), `telegram_delivery_enabled`, `effective_at`, and `created_at`. Subscription references and user references cascade on deletion; market and preset references restrict deletion. The latest-state index is `(subscription_id,effective_at DESC,sequence DESC)`; occurrence lookup uses `(supported_market_id,signal_preset_id,effective_at DESC,sequence DESC)`. Existing subscriptions receive one baseline false state row during migration; migration does not infer eligibility from old signal history or create notification work.

`signal_evaluation_states` has a unique market/preset pair, status (`warming`, `ready`, `stale`, `error`, `disabled`), safe reason, last candle/revision/open time/relation and values, calculation-state version `1`, JSON calculation state, and timestamps. It is mutable evaluator state; market FK CASCADE and preset/candle FKs RESTRICT. Its status/update index supports maintenance.

`signal_events` is global immutable history, not per-user copies. It contains an identity-generated stream sequence (unique), market/preset/trigger-candle FKs RESTRICT, unique trigger identity and occurrence tuple, full market/preset/calculation/candle/value snapshots, backfill flag and occurrence/creation timestamps. A new event, its feed stream row, and one `signal_telegram_dispatches` row are inserted atomically; recipient outbox rows are created later by the dispatcher. Occurred, market/preset/occurred, and trigger-candle indexes support retrieval/rebuild. `signal_event_invalidations` records at most one immutable invalidation per event, with reason (`candle_corrected`, `preset_disabled`, `calculation_invariant`) and optional replacement candle/revision; its FKs restrict deletion and an event index supports joins. See [STRATEGIES.md](STRATEGIES.md) and [ALERTS.md](ALERTS.md).

`signal_feed_stream_events` is a separate durable transport cursor log. Its identity-generated `sequence` is the SSE resume cursor; `kind` is `signal_created` or `signal_invalidated`; `signal_event_id` references the immutable event with `ON DELETE RESTRICT`; and `created_at` records publication order. `(kind, signal_event_id)` is unique, with indexes on `created_at` and `signal_event_id`. It does not copy the signal snapshot. Event creation and invalidation insert their stream row and execute `pg_notify('freecoinalert_signal_feed', '{"sequence":"..."}')` in the same transaction; PostgreSQL delivers the notification only after commit.

## Historical Analysis Run Domain

`historical_analysis_runs` stores one authenticated user's bounded historical-analysis request and its safe lifecycle metadata. It contains a UUID primary key, the owner, `supported_market_id`, `signal_preset_id`, a UUID `idempotency_key`, immutable exchange/market/symbol and preset snapshots, server-resolved `calculation_version_snapshot`, `simulation_version`, `assumption_version`, UTC `analysis_start`/`analysis_end`, progress stage/percent, attempt and availability fields, cancellation/worker timestamps, safe `failure_code`, and created/updated timestamps. The request snapshot preserves the market and fixed preset meaning selected at creation; later dataset, simulation, report, and frontend work does not alter this row.

The stored columns are:

```text
id UUID PRIMARY KEY
user_id UUID NOT NULL
supported_market_id UUID NOT NULL
signal_preset_id UUID NOT NULL
status VARCHAR(32) NOT NULL
idempotency_key UUID NOT NULL
exchange_snapshot VARCHAR(32) NOT NULL
market_type_snapshot VARCHAR(32) NOT NULL
symbol_snapshot VARCHAR(32) NOT NULL
base_asset_snapshot VARCHAR(32) NOT NULL
quote_asset_snapshot VARCHAR(32) NOT NULL
preset_code_snapshot VARCHAR(96) NOT NULL
preset_version_snapshot INTEGER NOT NULL
preset_name_snapshot VARCHAR(128) NOT NULL
strategy_type_snapshot VARCHAR(32) NOT NULL
timeframe_snapshot VARCHAR(8) NOT NULL
direction_snapshot VARCHAR(32) NOT NULL
period_snapshot INTEGER NOT NULL
threshold_snapshot NUMERIC(38,18) NULL
price_input_snapshot VARCHAR(32) NOT NULL
calculation_version_snapshot VARCHAR(64) NOT NULL
simulation_version VARCHAR(64) NOT NULL
assumption_version VARCHAR(64) NOT NULL
analysis_start TIMESTAMP WITH TIME ZONE NOT NULL
analysis_end TIMESTAMP WITH TIME ZONE NOT NULL
progress_stage VARCHAR(32) NOT NULL
progress_percent INTEGER NOT NULL DEFAULT 0
attempt_count INTEGER NOT NULL DEFAULT 0
max_attempts INTEGER NOT NULL DEFAULT 3
available_at TIMESTAMP WITH TIME ZONE NOT NULL
locked_at TIMESTAMP WITH TIME ZONE NULL
locked_by VARCHAR(64) NULL
cancellation_requested_at TIMESTAMP WITH TIME ZONE NULL
started_at TIMESTAMP WITH TIME ZONE NULL
completed_at TIMESTAMP WITH TIME ZONE NULL
failed_at TIMESTAMP WITH TIME ZONE NULL
cancelled_at TIMESTAMP WITH TIME ZONE NULL
failure_code VARCHAR(64) NULL
created_at TIMESTAMP WITH TIME ZONE NOT NULL
updated_at TIMESTAMP WITH TIME ZONE NOT NULL
```

The status is one of `queued`, `running`, `succeeded`, `failed`, or `cancelled`. Lifecycle checks require queued rows to have no terminal timestamps, running rows to have `started_at` and no terminal timestamp, succeeded rows to have `completed_at`, failed rows to have `failed_at` and a failure code, and cancelled rows to have `cancelled_at`. `analysis_end > analysis_start`, progress is 0 through 100, and attempts are nonnegative and bounded by `max_attempts` (default 3). The unique `(user_id, idempotency_key)` constraint makes create replay owner-scoped and prevents a key from creating a second logical run. Owner listing uses `(user_id, created_at DESC, id DESC)`; future queued work uses a partial `(available_at, created_at)` index; active-owner limits use a partial user/status index.

The user foreign key cascades on account deletion. Supported-market and signal-preset foreign keys use `ON DELETE RESTRICT` so a run retains the references required by its immutable request snapshot. Run creation validates configuration, range, ownership, and limits and then inserts the queued row in one transaction; it does not read candle rows or call a provider. Cancellation locks the owner row, immediately transitions queued work to cancelled or records `cancellation_requested_at` for running work, and commits the lifecycle change. There is no cleanup process in this change; terminal-run retention remains unresolved until the future worker/report boundary, and active runs must never be deleted automatically.

## Historical Analysis Dataset Domain

`historical_analysis_datasets` stores one canonical coverage manifest per run. Its `status` is `ready`, `failed`, or `stale`; a failed row contains one safe preparation failure category and no snapshot candle rows. A ready row records the fixed timeframe, user-visible analysis range, exact warm-up boundary/count, analysis/total counts, first/last stored boundaries, lowercase SHA-256 `manifest_fingerprint`, and preparation/staleness timestamps. The run FK cascades, while market and preset FKs restrict deletion. Counts are nonnegative, `total_candle_count = warmup_candle_count + analysis_candle_count`, and the maximum stored dataset size is 2,500 candles. Ready rows have no failure or stale timestamp; stale rows require `historical_dataset_stale` and `stale_at`.

`historical_analysis_dataset_candles` is an immutable full-value snapshot of each selected current canonical candle. It stores the zero-based contiguous position, source candle UUID/revision, warm-up flag, timeframe and UTC boundaries, complete OHLCV/trade values, source kind/counts/fingerprint, and creation time. It has CASCADE deletion from the dataset and `ON DELETE RESTRICT` to `market_candles`, unique `(dataset_id, position)` and `(dataset_id, candle_id)`, and `(dataset_id, open_time)` plus `(candle_id, dataset_id)` indexes. The preparation service validates exact UTC continuity and counts before insertion; the pure engine consumes equivalent immutable snapshot inputs rather than mutable current candle rows. No worker invokes it yet.

The dataset columns are:

```text
id UUID PRIMARY KEY
run_id UUID NOT NULL UNIQUE
supported_market_id UUID NOT NULL
signal_preset_id UUID NOT NULL
status VARCHAR(32) NOT NULL
failure_code VARCHAR(64) NULL
timeframe VARCHAR(8) NOT NULL
analysis_start TIMESTAMP WITH TIME ZONE NOT NULL
analysis_end TIMESTAMP WITH TIME ZONE NOT NULL
warmup_start TIMESTAMP WITH TIME ZONE NOT NULL
required_warmup_candles INTEGER NOT NULL
warmup_candle_count INTEGER NOT NULL
analysis_candle_count INTEGER NOT NULL
total_candle_count INTEGER NOT NULL
first_open_time TIMESTAMP WITH TIME ZONE NOT NULL
last_close_time TIMESTAMP WITH TIME ZONE NOT NULL
manifest_fingerprint VARCHAR(64) NOT NULL
prepared_at TIMESTAMP WITH TIME ZONE NOT NULL
stale_at TIMESTAMP WITH TIME ZONE NULL
created_at TIMESTAMP WITH TIME ZONE NOT NULL
updated_at TIMESTAMP WITH TIME ZONE NOT NULL
```

The snapshot columns are:

```text
id UUID PRIMARY KEY
dataset_id UUID NOT NULL
position INTEGER NOT NULL
candle_id UUID NOT NULL
candle_revision INTEGER NOT NULL
is_warmup BOOLEAN NOT NULL
timeframe VARCHAR(8) NOT NULL
open_time TIMESTAMP WITH TIME ZONE NOT NULL
close_time TIMESTAMP WITH TIME ZONE NOT NULL
open_price NUMERIC(38,18) NOT NULL
high_price NUMERIC(38,18) NOT NULL
low_price NUMERIC(38,18) NOT NULL
close_price NUMERIC(38,18) NOT NULL
base_volume NUMERIC(38,18) NOT NULL
quote_volume NUMERIC(38,18) NOT NULL
trade_count BIGINT NOT NULL
source_kind VARCHAR(32) NOT NULL
source_candle_count INTEGER NOT NULL
expected_source_candle_count INTEGER NOT NULL
source_fingerprint VARCHAR(64) NULL
created_at TIMESTAMP WITH TIME ZONE NOT NULL
```

The fingerprint schema version is `historical_dataset_fingerprint_v1`. It serializes the pinned market/preset/calculation identity, timeframe/range/warm-up metadata, and each snapshot's UUID, revision, UTC boundary, normalized decimal values, trade count, and source metadata in ascending position order. A ready dataset is reproducible from its immutable snapshot, while current-source validation can mark it stale after a correction.

## Cross-Domain Transaction Boundaries

Historical-analysis creation locks the user-scoped create boundary, validates server-controlled market/preset/range identity, and inserts the queued run atomically; idempotent replays do not create another row. Cancellation locks the owner row and commits its lifecycle/requested-cancellation transition atomically.

Dataset preparation locks the run, takes a short `FOR SHARE` snapshot lock over the selected current canonical candles, validates coverage, and inserts the dataset metadata and immutable candle rows in one transaction. Typed coverage failures persist only failed dataset metadata. Current-source validation locks the dataset and referenced market-candle rows for the check and atomically marks a changed dataset stale; it never rebuilds the same run.

Registration/login commit user/session together. Price-alert evaluation inserts event/outbox and transitions the alert atomically. Signal evaluation locks/updates its market-preset state and inserts a deduplicated signal event, its feed stream row, and its one dispatch row atomically. Signal invalidation inserts its immutable invalidation and feed stream row atomically. Subscription lifecycle and Telegram-preference transitions update the mutable subscription row and insert one state-history row atomically; equivalent preference requests insert neither a new state row nor notification work. Dispatcher pages select occurrence-time state, create idempotent per-user outbox rows, advance the subscription cursor, and update counts in one transaction. The PostgreSQL notification is emitted before the occurrence transaction commits and carries only the stream sequence. Telegram sending changes only outbox delivery state after the occurrence and fan-out transactions.

## Retention and Cleanup

Canonical candle retention defaults to 180 days; processed Telegram updates default to 30 days; signal-event retention configuration defaults to 365 days but no automatic signal-event deletion process is implemented. Feed stream cursor rows are retained for 7 days and the API listener deletes at most 10,000 expired rows in one maintenance transaction, without deleting referenced signal events. Signal dispatch and preset-signal outbox rows have no automatic cleanup in this change; terminal state remains available for recovery diagnosis and is governed by account-deletion FKs and future operational policy. Historical-analysis runs and datasets have no cleanup process in this change; active runs and referenced datasets must not be deleted automatically. The dataset candle FK restricts canonical candle retention, so terminal-run/dataset cleanup remains unresolved until the worker/report boundary defines it. Price events, alert records, and account-deletion retention remain governed by their FKs and operational policy.

## Migration Inventory

`20260728_0001` users/auth sessions; `20260730_0002` Telegram persistence; `0003` notification outbox; `0004` supported market catalogue; `0005` price alerts/events; `0006` live market state; `0007` price-alert notification kind; `0008` canonical candles; `0009` candle operational state; `0010` signal presets/subscriptions; `20260731_0011` signal evaluation/events/invalidations; `20260802_0012` durable signal-feed stream events and existing-event replay rows; `20260802_0013` explicit signal Telegram-delivery preference and immutable subscription state history with baseline rows; `20260802_0014` signal Telegram dispatch rows and preset-signal outbox references/indexes; `20260803_0015` owner-scoped historical-analysis runs; `20260803_0016` canonical historical-analysis dataset manifests and immutable candle snapshots. The chain head is `20260803_0016`.

## Backup, Deletion, and Unresolved Storage Concerns

Production backup, restore testing, account deletion, and production migration rollout have no implemented operational policy. These are unresolved deployment risks, not claims of existing behavior.

## Verification Status

Schema contents were read from the SQLAlchemy registry and Alembic chain. No migration, database connection, or schema verification command was run.
