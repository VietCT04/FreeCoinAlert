# Alerts and Signal Occurrences

## Purpose and Terminology

One-time price alerts are user-owned, terminal alert rules. Preset signal occurrences are global market facts produced from confirmed candles; subscriptions control a user's visibility, not a per-user copy of an occurrence. Formula details are owned by [STRATEGIES.md](STRATEGIES.md); Telegram delivery is owned by [TELEGRAM.md](TELEGRAM.md).

## One-Time Price Alerts

### Creation Preconditions

Creation accepts only a ready controlled market, an exact positive decimal target aligned to its price rule, `cross_above` or `cross_below`, an authenticated owner, CSRF protection, and a UUID idempotency key. The owner must have a connected Telegram destination. Creation does not contact Binance or initialize evaluation.

### Lifecycle

An alert starts `active`; `triggered`, `disabled`, `deleted`, and `failed` are terminal. Deleting an active or disabled alert is a soft deletion, excludes it from normal listing and evaluation, and preserves immutable history. At most 20 alerts may be active for one user.

### Initialization and Crossing Semantics

The first accepted price event stores relation `below`, `equal`, or `above` without triggering. Later events use equality-aware crossing: above requires prior relation below or equal and current above; below requires prior relation above or equal and current below. Repeated same-side observations do not trigger. Per-alert stored provider event identity prevents replay after restarts; a fresh post-reconnect observation can record a crossing from persisted relation.

### Trigger Transaction

The evaluator locks the still-active alert and atomically writes one immutable alert event, terminal `triggered` lifecycle state, and `telegram_price_alert` outbox row. Event identity is `binance:spot:<SYMBOL>:aggTrade:<provider_event_id>` and the database permits one event per alert. Telegram delivery failure never re-arms the alert.

### Delivery Separation

An occurrence is not delivery. Price-alert reads expose a safe market-data and notification summary; notification worker status does not change the terminal alert state.

## Preset Signal Subscriptions

### Subscription Lifecycle

Subscriptions select an available fixed preset version for a ready market. They start enabled, can be disabled, and may be reactivated; the chosen version remains pinned. Creating a subscription has no Telegram prerequisite. A separate owner-scoped Telegram-delivery preference is disabled by default; enabling it requires an active subscription and a connected, non-degraded private Telegram destination. New subscriptions, reactivation, and subscription disable reset the preference to false. New subscription rows are blocked at 20 enabled subscriptions per user, but reactivating an existing disabled row does not recheck that count and can exceed 20; this is an active implementation limitation.

### Evaluation Preconditions

The singleton market stream evaluates only current complete `1h` and `4h` candles. It groups work by market/timeframe/preset calculation key, refuses unsafe `stale`, `gapped`, or `error` candle state, and stores a restart-safe evaluation state. Insufficient history leaves the state warming.

### Initialization and Crossing Semantics

The first successful calculation initializes prior values and relation without creating an event. Later calculations use the same equality-aware directional crossing rule: cross above is prior left `<=` prior right and current left `>` current right; cross below is prior left `>=` prior right and current left `<` current right.

### Global Signal Occurrences

A crossing writes one immutable global `preset_crossed` event keyed by market, preset/version, candle open time, and candle revision. It snapshots market and preset facts, calculation version, previous/current values, close, and whether it was backfilled. It is not copied per subscriber. A new non-backfilled occurrence also creates one durable dispatch row in the same transaction; recipient outbox jobs are created later by the bounded dispatcher. Subscription lifecycle and preference changes write separate immutable subscription state events so fan-out can evaluate eligibility at occurrence time without rewriting the occurrence.

### Telegram Fan-out Boundary

The dispatcher selects the latest subscription state at or before `signal_event.occurred_at`. Only `active` state with `telegram_delivery_enabled = true` qualifies. It then requires the user's current owned Telegram connection to be `connected` with `connected_at <= occurred_at`. Missing, linking, degraded, disconnected, or later-connected destinations increment the dispatch skip count and create no job. Backfilled events are marked `skipped` as `historical_backfill_not_delivered`; invalidated and older-than-`SIGNAL_TELEGRAM_FANOUT_MAX_AGE_SECONDS` events are skipped without recipient work. Each page advances its subscription cursor only in the same transaction as idempotent outbox inserts. See [TELEGRAM.md](TELEGRAM.md) for the outbox and provider boundary.

The notification worker treats each preset-signal outbox row as one logical provider send. It validates the immutable payload and rechecks the owned subscription, preference, event invalidation, and current connected destination immediately before Telegram contact. Delivery failure, retry, timeout, or uncertain outcome changes only the outbox row and never rewrites, re-arms, or invalidates the global signal event.

### Candle Corrections and Invalidations

When a candle changes revision, the affected evaluation state is marked stale with `candle_correction_rebuild_required`. Immutable occurrences remain intact; a historical rebuild may add invalidation records and replacement revisions.

### Historical Simulation Boundary

The pure historical-analysis engine recalculates fixed-preset values from an immutable dataset snapshot and applies the same equality-aware crossing semantics as live evaluation. The separate worker invokes it and persists an immutable report, but it does not read or create `signal_events`, change live evaluation state, create subscriptions or alerts, or create Telegram work. Historical simulation is hypothetical analysis; it is separate from a global signal occurrence, in-app visibility, and provider delivery. The authenticated browser presentation is a separate server-report consumer and does not calculate indicators or metrics.

## Deduplication and Restart Safety

Price alerts deduplicate by alert and provider-event identity; global signals deduplicate their immutable trigger identity. Signal dispatches deduplicate by signal event, while per-user outbox jobs use both the existing user/idempotency key and a partial user/event uniqueness rule. Stored relation, last provider/candle identity, durable cursors, and database constraints make repeated inputs safe. Automatic evaluator restart catch-up is not implemented: the evaluator handles only newly supplied confirmed-candle events, and `SIGNAL_LIVE_CATCHUP_MAX_DAYS=7` is reserved configuration.

## Signal Feed Visibility and Recovery

Price alerts and their events are visible only to their owner. Signal subscriptions are user-owned current rows; reactivation replaces their activation timestamp and clears the disabled timestamp, so complete historical subscription intervals are not retained in the mutable row. Immutable subscription state events preserve lifecycle and Telegram-preference state at each effective time. Global signal events remain separate from per-user visibility, preference, and delivery.

`GET /signal-feed` exposes global signal history through matching active or disabled subscription rows owned by the authenticated user. It orders immutable snapshots by occurrence time and event UUID, supports current/invalidated/all filtering, and returns an opaque history cursor plus a durable stream watermark. A historical row is strategy history, not proof that the user received a notification.

`GET /signal-feed/stream` is a credentialed one-way SSE connection. It delivers only events matching currently active subscriptions, uses the durable stream sequence for `Last-Event-ID` recovery, and sends replay records separately from newly live records. A stream reset or retained-cursor gap sends the user back to the historical endpoint. Signal invalidations update the prior feed state and are never presented as a new positive occurrence. In-app feed delivery remains separate from signal occurrence state and Telegram delivery.

The authenticated browser section presents one-time price alerts as status-filtered responsive cards with a dialog-based create flow, server-provided evaluation and market-data status, and confirmed deletion only for active or disabled alerts. Preset signals use separate Presets and Signal history tabs; the preset view has client-side market/timeframe/subscription display filters, fixed technical details, server-confirmed subscribe/disable actions, and a server-owned Telegram-delivery switch. Both tab contents remain mounted while the route is mounted, so the existing feed, replay recovery, visibility handling, cursor, and sound state are not silently restarted by tab changes. `View history` selects the existing preset filter, switches to the history tab, and moves focus to its heading. Enabling Telegram delivery uses confirmation, disabling is direct, and readiness changes from the Telegram connection page refresh the subscription response. A genuinely new visible SSE signal is highlighted for five seconds; replay, pagination, refresh, visibility recovery, and invalidation updates do not receive the live highlight or sound. Browser history and sound remain independent from Telegram delivery.

The browser merges feed entries by immutable signal-event ID, updates invalidations on the existing entry, orders by occurrence time then event ID, and bounds recent SSE sequence deduplication to 2,000 entries in memory. Feed events and sequences are never stored in browser persistence.

The repository-owned browser journeys cover alert creation readiness, validation, idempotency, live evaluation states, provider-data warnings, owner-scoped filtering, pagination, and confirmed deletion through the real API and provider simulator. The exact route/action status is recorded in [E2E_COVERAGE.md](E2E_COVERAGE.md); these journeys are Implemented and Verified through the latest full isolated E2E pass.

## Current Limits

- Maximum active price alerts per user: 20.
- New signal subscription rows are limited to 20 enabled subscriptions per user. Reactivation can exceed that limit; see [CONCERNS.md](CONCERNS.md).

### Historical event and feed controls

`SIGNAL_HISTORY_DAYS=90` is currently used only by the placeholder backfill coverage check. `SIGNAL_EVENT_RETENTION_DAYS=365` has no cleanup implementation. Feed transport cursors use a separate 7-day `SIGNAL_STREAM_RETENTION_DAYS` log; signal events remain the historical source of truth after cursor cleanup.

## Not Supported

Custom alerts, recurring indicator alerts, arbitrary periods, multi-condition rules, cooldowns, edits, trading, system/mobile push notifications, custom sounds, and live alert/signal charts are not supported. Browser signal-feed controls, optional in-page sound, Telegram-delivery controls, and the historical-analysis report presentation are separate from one another and from global occurrence/provider delivery. Durable preset fan-out and preset Telegram provider delivery remain separate from browser presentation.

## Verification Status

The lifecycle and evaluator code were inspected statically, and the covered live crossings, provider warnings, and delivery-queued browser paths passed in the isolated E2E suite. Restart/catch-up, correction rebuild, and production delivery behavior remain unverified.
