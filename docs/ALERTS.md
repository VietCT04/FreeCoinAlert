# Alerts

## Purpose

## Preset subscriptions

Signal subscriptions are distinct from one-time price alerts. They are durable user-owned selections for the future website signal feed, and do not themselves calculate indicators, create occurrences, or enqueue Telegram notifications. Historical signal occurrences added later are global market events; users may view retained matching history for a subscription they currently have or previously had, including occurrences before activation. Those entries must be described as historical signal occurrences, not historical deliveries.

This document defines alert types, lifecycle, evaluation modes, state, cooldown behavior, reproducibility, event creation, and duplicate prevention.

## Alert Categories

### Immediate Price Alerts

Examples:

- Price is above a threshold.
- Price is below a threshold.
- Price crosses above a threshold.
- Price crosses below a threshold.

These may evaluate from real-time ticker or trade events.

Crossing alerts require previous-state tracking. A stream of prices remaining above a threshold must not repeatedly trigger `cross above`.

### Candle-Close Indicator Alerts

Examples:

- RSI falls below 30 on `1h`.
- MACD crosses above its signal line on `1h`.
- EMA 20 crosses above EMA 50 on `4h`.
- Volume exceeds a defined multiple of its moving average.

These evaluate only after the relevant candle closes in the initial product.

Intrabar indicator evaluation is a later feature requiring explicit user-facing semantics.

## Alert Definition

An alert must identify:

- Owner
- Exchange
- Market type
- Symbol
- Timeframe
- Evaluation mode
- Strategy template version or custom rule definition
- Notification destination
- Cooldown
- Status
- Rule-schema version
- Creation and update timestamps

The backend validates the complete definition before activation.

## Lifecycle

Suggested states:

- `DRAFT` when incomplete alert editing is introduced
- `ACTIVE`
- `PAUSED`
- `DISABLED`
- `DELETED` or soft-deleted, depending on later retention decisions

The exact enum must be approved with the schema issue.

State transitions must be explicit. A disabled alert caused by invalid market data or delivery failure must not silently reactivate.

### One-Time Price-Cross Lifecycle

Issue #29 fixes the initial one-time price-cross states as `active`, `triggered`, `disabled`,
`deleted`, and `failed`. A new alert is `active` and has no crossing state until its first accepted
market observation. The first observation initializes `below`, `equal`, or `above` without triggering.
Later accepted observations may change that relation; repeated observations on the same relation do
not need to write state.

`triggered`, `disabled`, `deleted`, and `failed` are terminal. `triggered` records exactly one immutable
event and can never return to `active`. `disabled` records a stable product reason such as
`user_disabled` or `market_disabled`; delivery failure is not an alert failure. User-facing deletion
soft-deletes only pending active alerts, excludes them from normal lists and evaluation, and retains
the row and any immutable history.

## Evaluation State

## Browser One-Time Price Alert Flow

Issue #33 places the minimal authenticated price-alert form and stacked alert cards on the root route after the
Telegram connection section. It offers only available catalog markets, exact string target input, cross-above or
cross-below direction, creation, first-page refresh, cursor-based load-more, and explicit deletion of eligible
active or disabled alerts. It does not display a ticker or chart, edit or reactivate alerts, expose internal
identifiers, or conflate a terminal trigger with Telegram delivery state.

Depending on rule type, an alert may need durable state such as:

- Previous comparison result
- Previous indicator values
- Last evaluated candle
- Last triggered time
- Last trigger identity
- Current side of a price threshold
- Cooldown end time

State must survive process restarts when losing it could cause duplicate or missed alerts.

## Crossovers

A crossover occurs when the relative ordering changes between two consecutive evaluated points.

For `cross above`:

```text
previous_left <= previous_right
and
current_left > current_right
```

The implementation must define behavior when values are equal or unavailable and use the same behavior in live and historical evaluation.

## Cooldown

Cooldown prevents repeated user notifications after triggers that remain active or occur frequently.

Cooldown is not a substitute for correct crossover or deduplication logic.

The product must show:

- Cooldown duration
- Whether cooldown starts at trigger creation or successful delivery
- Whether events are recorded but notifications suppressed during cooldown

The initial decision should be made by a focused issue.

## Alert Events

A trigger creates an immutable alert event containing enough information to reproduce and explain it:

- User alert ID
- Strategy or rule version
- Exchange, market, and symbol
- Timeframe and evaluation mode
- Candle open time or real-time event reference
- Trigger price
- Relevant indicator snapshot
- Trigger identity
- Creation timestamp

Do not mutate historical event meaning after a strategy template is updated.

## Deduplication

A logical trigger must have one stable deduplication key.

For candle-close alerts, the key should include the alert, strategy version, candle, and trigger identity.

For price alerts, the key must account for crossing state and restart behavior.

Database constraints should enforce uniqueness where possible.

For the initial one-time price alert, the event key is
`binance:spot:<SYMBOL>:aggTrade:<provider_event_id>`. The database permits only one event per alert
and also uniquely stores that alert-scoped trigger identity. The future evaluator must lock the alert,
ignore aggregate-trade IDs that are not greater than the persisted ID, and create the event within its
coordinating transaction.

## Notification Creation

When an alert triggers:

1. Validate that the alert is still active.
2. Create the alert event.
3. Create the notification-outbox record.
4. Commit both atomically.
5. Allow the notification worker to send independently.

A triggered alert and a delivered notification are separate states.

## Shared Calculation

Do not calculate the same indicator separately for every user.

Share calculations using a key equivalent to:

```text
exchange + market + symbol + timeframe + indicator + parameters
```

User rules then compare shared outputs against their own thresholds or conditions.

Correctness is more important than optimization; introduce shared caches only with clear invalidation and consistency rules.

## Failure Behavior

- If market data is stale or incomplete, do not evaluate rules as though data were current.
- If an aggregate candle is incomplete, do not evaluate candle-close strategies from it.
- If notification delivery fails, preserve the alert event and retry the delivery job according to policy.
- If a rule becomes invalid after a supported-market change, disable it explicitly and inform the user when possible.

## User-Facing Requirements

Before activation, show:

- Symbol and market
- Timeframe
- Exact condition
- Evaluation mode
- Cooldown
- Telegram destination

Alert history should distinguish:

- Triggered and delivered
- Triggered and pending
- Triggered and retrying
- Triggered but permanently failed

## Testing Expectations

Prioritize tests for:

- Above/below and crossing semantics
- Equality behavior
- Restart and reconnect state
- Candle-close-only evaluation
- Cooldown boundaries
- Duplicate event processing
- Atomic event and outbox creation
- Shared calculation consistency

## Pending Decisions

- Exact alert statuses.
- Initial cooldown defaults and limits.
- Behavior for events suppressed during cooldown.
- Whether users can edit active alerts or changes create a new version.
- Maximum active alerts per user.
- Data-staleness threshold for suspending evaluation.

## One-Time Price Alert API

Issue #30 adds authenticated create, owned list/read, and CSRF-protected soft-delete behavior. Creation requires
a connected Telegram destination, a canonical ready market, exact target validation, UUID idempotency, and fewer
than 20 active rows. Deleted alerts are excluded from normal lists; active and disabled rows become terminal
`deleted` with `user_deleted`, while triggered and failed rows cannot be deleted or reactivated. The API does
not inspect a price: a future first accepted market event initializes relation without triggering. Event and
outbox creation remain future evaluator work.

## One-Time Price Evaluation

Issue #32 evaluates accepted ordered `PriceEvent` values inside the singleton market-stream process. Active
alerts are grouped in an in-memory registry by supported market, refreshed every two seconds with a five-second
overlap and rebuilt every 60 seconds. The first accepted price records `below`, `equal`, or `above` without a
trigger. `cross_above` triggers only from below/equal to above; `cross_below` triggers only from above/equal to
below. Same-side observations do not write the alert row.

Each candidate re-locks and revalidates the durable active alert. A successful crossing atomically creates the
immutable event, terminal `triggered` transition, and one Telegram outbox job. The event identity is
`binance:spot:<SYMBOL>:aggTrade:<provider_event_id>`; reconnect observations use the first accepted fresh price,
not an invented outage-time value. Delivery failure never re-arms a triggered alert. Markets that are no longer
ready disable their active alerts with `market_disabled`; impossible persisted evaluation state fails the alert with
`evaluation_invariant`.
