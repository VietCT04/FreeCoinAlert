# Telegram

## Purpose and Current Scope

Telegram is the sole implemented notification provider. It supports one private-chat destination per user, browser-issued deep links, long polling, test messages, and durable price-alert delivery. Signal occurrences now have a separate database fan-out boundary that can create durable preset-signal outbox jobs for occurrence-time eligible users; the notification worker does not yet send that kind. Preset-signal provider delivery and browser controls remain planned. Exact HTTP contracts are in [API.md](API.md); persisted fields are in [DATABASE.md](DATABASE.md).

## Configuration and Optional Startup

`TELEGRAM_BOT_USERNAME` is public optional configuration for browser links. `TELEGRAM_BOT_TOKEN` is secret and required by the poller and notification worker, not API startup. The Compose `telegram` profile starts `telegram-updates`, `signal-telegram-dispatcher`, and `notification-worker`; the dispatcher needs only `DATABASE_URL` and fan-out settings and none is part of the default stack.

## Browser Linking Flow

An authenticated, CSRF-protected link request creates `https://t.me/<username>?start=<token>`. The browser receives only a safe `linking` response and expiry. Link creation rejects missing configuration, an already connected/degraded destination, or unavailable persistence. A new link replaces outstanding unused links.

## Link-Token Security and Lifecycle

Tokens are securely random, URL-safe values. Only their SHA-256 hash is stored. A token expires after `TELEGRAM_LINK_TTL_SECONDS` (600 by default), is single use, and can be revoked by replacement or disconnect. A token belongs to a user, not a connection. Missing, expired, consumed, revoked, or ownership-conflicting tokens are recorded as safe outcomes without exposing an internal user ID.

## Telegram Update Poller

The optional poller uses long polling with `concurrent_updates(False)`, requests only message updates, and does not drop pending updates. It accepts private `/start <token>` and addressed `/start@<bot_username> <token>` commands. It records `update_id` before processing, so duplicate updates are ignored. A successful link is committed before one confirmation attempt; an uncertain or failed confirmation is recorded but not retried. Processed-update cleanup runs at startup when due, with 30-day retention by default. A Telegram webhook conflict stops polling safely.

## Connection Lifecycle

Persisted states are `connected`, `degraded`, and `disconnected`; `linking` and `not_connected` are safe derived API states. A matching disconnected destination can reactivate; a different user or destination creates an ownership conflict. Disconnect is idempotent, marks the saved connection `disconnected` with a safe reason, and revokes outstanding tokens. Safe responses never include IDs, chat IDs, token hashes, or raw tokens.

## Preset Signal Delivery Preference and Fan-out

Each owned signal subscription stores `telegramDelivery.enabled`, disabled by default, plus its last preference-change timestamp. The authenticated subscription response derives `telegramDelivery.readiness` once per request as `ready`, `linking`, `not_connected`, or `degraded` without storing or exposing provider identifiers. `PUT /signal-subscriptions/{id}/telegram-delivery` is authenticated and CSRF-protected, owner scoped, and limited to 30 mutations per user per 15 minutes. Enabling requires an active subscription and a connected, non-degraded destination; disabling is always allowed and idempotent. Disconnecting Telegram changes readiness only and does not change the stored preference.

Subscription creation, reactivation, disable, and preference changes record immutable occurrence-time state rows in the same transaction. A new non-backfilled signal occurrence creates one dispatch row atomically with the immutable occurrence and feed stream row. The separate dispatcher selects the latest state at `occurred_at`, requires active state with delivery enabled, checks the current owned connection is connected with `connected_at <= occurred_at`, and creates at most one immutable-snapshot `telegram_preset_signal` outbox job per user and occurrence. Missing, linking, degraded, disconnected, or later-connected destinations increment `skipped_count` without creating a job. Backfilled, invalidated, and expired occurrences are skipped; the dispatcher does not wait for reconnection or contact Telegram. Existing subscriptions are migrated with delivery disabled and a false baseline state; old signal history receives no dispatch rows.

## Test Notifications

An authenticated CSRF-protected request with a UUID idempotency key creates a `telegram_test` outbox job without a body. It is limited to three new requests per user per 15 minutes; an idempotent replay returns the original safe job. It requires a connected, non-degraded destination. `queued`, `sending`, `retrying`, `sent`, and `failed` describe provider-processing state, not device receipt.

## Price-Alert Notifications

The price-alert trigger transaction creates its immutable alert event and a `telegram_price_alert` outbox row. The worker formats the stored snapshot as a plain UTC message. A triggered alert is final regardless of sending, retrying, or failing delivery.

## Notification Outbox

Outbox jobs hold the owned user/destination reference, kind, idempotency key, immutable payload, status, attempts, claim/next-attempt timestamps, safe failure category, and provider message ID. `telegram_preset_signal` jobs also hold restricted `signal_event_id` and `signal_subscription_id` references and require both fields. The uniqueness scope is `(user_id, idempotency_key)` across notification kinds, with a partial `(user_id, signal_event_id)` uniqueness rule for preset-signal jobs. The user FK cascades deletion; the connection, signal-event, and signal-subscription FKs restrict deletion.

## Worker Claim, Send, Retry, and Recovery

The optional notification worker claims only the currently supported `telegram_test` and `telegram_price_alert` jobs in short transactions using lock-safe claims, then releases the database lock before the network request. Preset-signal jobs remain durable and pending until the separately approved provider-delivery change. The signal dispatcher has its own `FOR UPDATE SKIP LOCKED` claims, bounded subscription pages, stale-claim requeue, database retry, expiry, and attempt limit; it never performs a provider request. The notification worker rechecks that its destination is still connected and owned. Confirmed sends record the provider message ID. Known temporary failures move to `retrying` using bounded backoff; permanent failures become `failed`. Timeouts and uncertain provider outcomes become an outcome-unknown failure to avoid duplicate messages. A later worker detects stale `processing` claims and terminally marks them `failed` as `telegram_delivery_outcome_unknown`; it never requeues them because provider outcome is uncertain. No queue broker is used.

## Delivery Status and User-Facing Meaning

`queued`, `sending`, and `retrying` mean the platform has not confirmed delivery. `sent` means Telegram accepted the send request, not that the device displayed it. `failed` is a safe terminal processing failure. Connection degradation maps to safe user-facing unavailable/degraded status rather than provider details.

## Disconnect and Provider-Failure Behavior

Disconnect prevents future delivery through that destination. Provider blocking, invalid chats, missing configuration, transport failure, and rate limiting are categorized safely and do not reveal Telegram internals. A failed Telegram send never changes a price alert back to active.

## Stored and Prohibited Telegram Data

Stored identity is limited to Telegram user ID, private chat ID, optional username, connection timestamps/status/reason, processed update ID/outcome, token hash/lifecycle, and provider message IDs. Raw link tokens, bot tokens, webhook secrets, user-supplied chat IDs, and provider payloads are neither returned nor logged.

## Not Supported

Groups, channels, multiple destinations, user-supplied chat IDs, webhooks, scheduled polling infrastructure, preset-signal provider messages, browser controls for the preference, and additional notification channels are not implemented. Durable preset-signal fan-out is implemented separately from provider sending.

## Verification Status

Linking, long polling, provider sends, retries, and device receipt were not exercised; implementation was inspected statically.
