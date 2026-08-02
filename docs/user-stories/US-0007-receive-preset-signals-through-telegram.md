# US-0007: Receive Preset Signals Through Telegram

## User Story

As a user, I want selected preset signals delivered to my connected Telegram chat, so that I can receive important signal occurrences without keeping the website open.

## Context

FreeCoinAlert already separates several concepts:

- A fixed preset defines a versioned strategy.
- A subscription records a user's interest in a preset for a supported market.
- A global signal occurrence records that the preset crossed on a confirmed candle.
- The authenticated feed controls in-app visibility.
- Browser sound is a separate local presentation preference.
- Telegram delivery is a provider outcome and must not change the occurrence itself.

Preset signal occurrences currently do not create Telegram notification work. Telegram delivery must be an explicit per-subscription choice, use the user's owned private destination, remain restart-safe, and avoid duplicates across retries, replay, and reconnects.

## Acceptance Criteria

- [ ] A user can explicitly enable or disable Telegram delivery for each owned preset subscription.
- [ ] Telegram delivery is not silently enabled for existing subscriptions.
- [ ] Subscription state, feed visibility, browser sound, Telegram-delivery preference, signal occurrence, and provider delivery outcome remain separate concepts.
- [ ] Only an eligible active subscription with Telegram delivery enabled can create notification work for a new matching signal occurrence.
- [ ] The system defines safe behavior when Telegram is not connected, linking, degraded, disconnected, replaced, or blocked.
- [ ] Each user receives at most one logical Telegram notification for the same eligible signal occurrence.
- [ ] Evaluator replay, stream replay, retries, reconnects, worker restarts, and repeated database reads do not create duplicate logical notifications.
- [ ] Existing historical occurrences are not delivered retroactively unless a later separately approved feature explicitly requests replay.
- [ ] Disconnecting Telegram prevents future delivery through that destination without disabling the preset subscription or removing feed history.
- [ ] Disabling Telegram delivery does not disable the preset subscription.
- [ ] Signal occurrence persistence does not depend on Telegram provider availability.
- [ ] Delivery failure, retry, timeout, or uncertain provider outcome does not delete, rewrite, re-arm, or invalidate the signal occurrence.
- [ ] A Telegram message clearly identifies the market, fixed preset, timeframe, direction, occurrence time, relevant values, and strategy version using immutable safe snapshots.
- [ ] Telegram messages remain informational and do not claim profit, prediction, guaranteed delivery, or financial advice.
- [ ] Ownership and authorization are enforced server-side; callers cannot select another user's subscription or Telegram destination.
- [ ] Bot tokens, raw provider responses, chat IDs, internal user IDs, and unnecessary personal data are not exposed to browser clients or logs.
- [ ] Loading, pending, disconnected, degraded, success, retrying, failed, rate-limited, stale-session, and unavailable states are communicated safely where user-facing.
- [ ] Relevant product, API, database, architecture, security, alert, Telegram, operations, observability, README, concerns, and continuity documentation is updated with each implementation change.

## Delivery Principles

### Explicit Opt-In

Telegram delivery is a per-subscription preference. Creating or reactivating a subscription must not silently imply Telegram delivery unless a future approved requirement changes that rule.

### Occurrence and Delivery Separation

A global occurrence is an immutable market fact. Recipient selection, durable notification work, provider processing, and user-visible delivery status are separate layers.

### No Automatic Historical Replay

Enabling Telegram delivery affects future eligible occurrences. Existing feed history is not converted into queued Telegram notifications by default.

### Idempotency

The system needs a stable logical identity connecting the user, subscription or delivery policy, signal occurrence, destination policy, and notification job so repeated processing remains safe.

### Private Destination Only

This story uses the existing one-private-chat-per-user Telegram model. Groups, channels, manually entered chat IDs, and multiple destinations remain unsupported.

## Out of Scope

- Global notification preferences
- Quiet hours or schedules
- Batched or digest notifications
- Multiple Telegram destinations
- Telegram groups or channels
- Email, SMS, push notifications, or custom webhooks
- Retroactive delivery of historical signal occurrences
- User-authored strategies or arbitrary indicator rules
- Trading execution, exchange API keys, financial advice, or performance guarantees
- Changing feed ordering, SSE replay semantics, browser sound semantics, or preset calculations

## Risks

- Recipient fan-out can create duplicate or missing notifications if occurrence, preference, destination, and outbox identities are not defined precisely.
- A user's destination or delivery preference may change between occurrence time and provider send time.
- A timeout can leave the Telegram provider outcome unknown; unsafe retries may duplicate messages.
- Large future subscriber counts may make synchronous fan-out expensive without a bounded recovery design.
- Delivery-status exposure can leak internal or cross-user state if ownership is not enforced consistently.
- Users may confuse a signal occurrence with a prediction or assume that Telegram acceptance proves device receipt.

## Follow-up Issues

- #71 — Add per-subscription Telegram delivery preference and API
- #72 — Fan out eligible signal occurrences to durable Telegram jobs
- #73 — Deliver preset signal jobs through the notification worker
- #74 — Add Telegram delivery controls for preset subscriptions

Implementation order:

```text
#71 → #72 → #73 → #74
```

Issue #74 also depends on the preset-subscription and signal-feed frontend from Issue #54 being merged.

Each implementation issue requires an explicitly approved technical solution comment before work begins.
