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

Subscriptions select an available fixed preset version for a ready market. They start enabled, can be disabled, and may be reactivated; the chosen version remains pinned. They have no Telegram prerequisite. At most 20 subscriptions per user may be enabled.

### Evaluation Preconditions

The singleton market stream evaluates only current complete `1h` and `4h` candles. It groups work by market/timeframe/preset calculation key, refuses unsafe `stale`, `gapped`, or `error` candle state, and stores a restart-safe evaluation state. Insufficient history leaves the state warming.

### Initialization and Crossing Semantics

The first successful calculation initializes prior values and relation without creating an event. Later calculations use the same equality-aware directional crossing rule: cross above is prior left `<=` prior right and current left `>` current right; cross below is prior left `>=` prior right and current left `<` current right.

### Global Signal Occurrences

A crossing writes one immutable global `preset_crossed` event keyed by market, preset/version, candle open time, and candle revision. It snapshots market and preset facts, calculation version, previous/current values, close, and whether it was backfilled. It is not copied per subscriber and creates no Telegram job.

### Candle Corrections and Invalidations

When a candle changes revision, the affected evaluation state is marked stale with `candle_correction_rebuild_required`. Immutable occurrences remain intact; a historical rebuild may add invalidation records and replacement revisions.

## Deduplication and Restart Safety

Price alerts deduplicate by alert and provider-event identity; global signals deduplicate their immutable trigger identity. Stored relation, last provider/candle identity, and database constraints make repeated inputs safe. Automatic restart catch-up is not implemented: the evaluator handles only newly supplied confirmed-candle events, and `SIGNAL_LIVE_CATCHUP_MAX_DAYS=7` is reserved configuration.

## Ownership and Visibility

Price alerts and their events are visible only to their owner. Signal subscriptions are user-owned current rows; reactivation replaces their activation timestamp and clears the disabled timestamp, so complete historical subscription intervals are not retained. Global signal events are separately persisted but have no feed API or frontend visibility behavior.

## Current Limits

- Maximum active price alerts per user: 20.
- Maximum enabled signal subscriptions per user: 20.

### Planned feed and history controls

`SIGNAL_HISTORY_DAYS=90` is currently used only by the placeholder backfill coverage check. `SIGNAL_EVENT_RETENTION_DAYS=365` has no cleanup implementation. Any historical signal visibility, feed retention, or subscription-interval semantics are planned rather than current behavior.

## Not Supported

Custom alerts, recurring indicator alerts, arbitrary periods, multi-condition rules, cooldowns, edits, trading, website notifications, sound, and a signal feed are not implemented.

## Verification Status

The lifecycle and evaluator code were inspected statically. Live crossings, restart/catch-up, correction rebuild, and delivery behavior are unverified.
