# Alerts

## Purpose

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

- RSI falls below 30 on `15m`.
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

## Evaluation State

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