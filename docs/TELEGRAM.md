# Telegram

## Purpose and Current Scope

Telegram is the sole implemented notification provider. It supports one private-chat destination per user, browser-issued deep links, long polling, test messages, durable price-alert delivery, preset-signal delivery from immutable outbox snapshots, and browser controls for the per-subscription delivery preference. Signal occurrences have a separate database fan-out boundary that creates jobs only for occurrence-time eligible users. Exact HTTP contracts are in [API.md](API.md); persisted fields are in [DATABASE.md](DATABASE.md).

## Configuration and Optional Startup

`TELEGRAM_BOT_USERNAME` is public optional configuration for browser links. `TELEGRAM_BOT_TOKEN` is secret and required for poller and provider requests, not API startup. The production defaults are `TELEGRAM_BOT_API_BASE_URL=https://api.telegram.org/bot`, `TELEGRAM_BOT_FILE_BASE_URL=https://api.telegram.org/file/bot`, and `TELEGRAM_PUBLIC_BOT_BASE_URL=https://t.me`. The notification worker can run without a token to mark claimed jobs with the safe terminal code `telegram_not_configured`, but normal delivery requires the token. The Compose `telegram` profile starts `telegram-updates`, `signal-telegram-dispatcher`, and `notification-worker` only after the shared API preparation and database migration services complete; the dispatcher needs only `DATABASE_URL` and fan-out settings and none is part of the default stack. Telegram startup is optional and a Telegram process failure does not block the core API/web stack.

## Browser Linking Flow

An authenticated, CSRF-protected link request creates `${TELEGRAM_PUBLIC_BOT_BASE_URL}/<username>?start=<token>`. The browser receives only a safe `linking` response and expiry. Link creation rejects missing configuration, an already connected/degraded destination, or unavailable persistence. A new link replaces outstanding unused links.

The isolated E2E overlay sets the Telegram API and file base URLs and the public bot base URL to the internal `provider-simulator:9000` endpoints. The simulator serves the public linking page, records the browser visit, and queues the corresponding private `/start` update. E2E controls can produce sent, temporary, permanent, rate-limited, and uncertain outcomes; an uncertain send closes the provider connection so the existing worker records `telegram_delivery_outcome_unknown`. Custom Telegram URLs are rejected unless E2E mode is enabled, and the E2E token/database guards prevent these settings from being used against the normal environment.

The browser journey specifications cover disconnected, linking, expiry, connected, refresh, test-message sent/temporary/rate-limited/permanent/uncertain outcomes, disconnect, and temporary-failure recovery states through the real API, poller, worker, and internal provider simulator. They never contact `t.me` or `api.telegram.org`; coverage status is in [E2E_COVERAGE.md](E2E_COVERAGE.md), and these simulator-backed journeys are Implemented and Verified through the latest full isolated E2E pass.

## Link-Token Security and Lifecycle

Tokens are securely random, URL-safe values. Only their SHA-256 hash is stored. A token expires after `TELEGRAM_LINK_TTL_SECONDS` (600 by default), is single use, and can be revoked by replacement or disconnect. A token belongs to a user, not a connection. Missing, expired, consumed, revoked, or ownership-conflicting tokens are recorded as safe outcomes without exposing an internal user ID.

## Telegram Update Poller

The optional poller uses long polling with `concurrent_updates(False)`, requests only message updates, and does not drop pending updates. It accepts private `/start <token>` and addressed `/start@<bot_username> <token>` commands. It records `update_id` before processing, so duplicate updates are ignored. A successful link is committed before one confirmation attempt; an uncertain or failed confirmation is recorded but not retried. Processed-update cleanup runs at startup when due, with 30-day retention by default. A Telegram webhook conflict stops polling safely.

The poller and notification worker obtain their clients through the centralized Telegram Bot factory, which applies the configured API and file base URLs consistently. No browser code constructs a provider client or receives the bot token.

## Connection Lifecycle

Persisted states are `connected`, `degraded`, and `disconnected`; `linking` and `not_connected` are safe derived API states. A matching disconnected destination can reactivate; a different user or destination creates an ownership conflict. Disconnect is idempotent, marks the saved connection `disconnected` with a safe reason, and revokes outstanding tokens. Safe responses never include IDs, chat IDs, token hashes, or raw tokens.

## Preset Signal Delivery Preference and Fan-out

Each owned signal subscription stores `telegramDelivery.enabled`, disabled by default, plus its last preference-change timestamp. The authenticated subscription response derives `telegramDelivery.readiness` once per request as `ready`, `linking`, `not_connected`, or `degraded` without storing or exposing provider identifiers. `PUT /signal-subscriptions/{id}/telegram-delivery` is authenticated and CSRF-protected, owner scoped, and limited to 30 mutations per user per 15 minutes. Enabling requires an active subscription and a connected, non-degraded destination; disabling is always allowed and idempotent. Disconnecting Telegram changes readiness only and does not change the stored preference.

The active preset card presents this server-owned preference separately from subscription status, browser history, and browser sound. It uses a visible On/Off switch, maps readiness to Ready, Linking, Not connected, or Needs attention guidance, confirms enabling before sending the CSRF-protected request, applies only the successful response, and allows direct disabling. Connection refresh, linking, recovery, and disconnect changes refresh the subscription list so readiness does not remain stale. The browser stores no Telegram preference, readiness, destination identifier, token, or provider payload.

The authenticated `/telegram` page presents connection status, linking guidance, test-message processing, an owner-scoped usage summary, and a confirmed destructive disconnect action. The usage summary reads active price alerts with `limit=20` and active subscriptions with Telegram delivery enabled through existing endpoints; each subsection can show unavailable independently. The page does not expose chat IDs, provider IDs, outbox state, or per-occurrence delivery history. A success toast is shown only after the server first reports a test notification as `sent`; queued, retrying, uncertain, and failed states remain inline.

Subscription creation, reactivation, disable, and preference changes record immutable occurrence-time state rows in the same transaction. A new non-backfilled signal occurrence creates one dispatch row atomically with the immutable occurrence and feed stream row. The separate dispatcher selects the latest state at `occurred_at`, requires active state with delivery enabled, checks the current owned connection is connected with `connected_at <= occurred_at`, and creates at most one immutable-snapshot `telegram_preset_signal` outbox job per user and occurrence. Missing, linking, degraded, disconnected, or later-connected destinations increment `skipped_count` without creating a job. Backfilled, invalidated, and expired occurrences are skipped; the dispatcher does not wait for reconnection or contact Telegram. Existing subscriptions are migrated with delivery disabled and a false baseline state; old signal history receives no dispatch rows.

## Preset-Signal Payload and Message

The notification worker accepts only schema version `1` with the exact `telegram_preset_signal` fields written by the dispatcher. It rejects unknown fields or versions, missing snapshots, invalid UUIDs or UTC timestamps, unsupported SMA/RSI strategy combinations, unsupported timeframes/directions/price inputs, invalid decimal strings, and non-finite values. A rejected job is terminally failed as `notification_payload_invalid` without a provider request.

Messages are plain text without Markdown parsing, rich media, charts, links, trading actions, or mutable current-market data. They identify the symbol, preset, timeframe, crossing direction, previous/current comparison values, candle close and quote asset, candle-close UTC time, preset code/version, calculation version, and the informational-only disclaimer. SMA comparisons use `Close` and `SMA 200`; RSI comparisons use `RSI 14` and `Threshold`. Every value is read from the validated immutable job payload.

The rendered layout is:

```text
FreeCoinAlert preset signal

<SYMBOL> · <PRESET NAME>
<TIMEFRAME> candle crossed <above|below>.

Previous:
<LEFT LABEL>: <PREVIOUS LEFT>
<RIGHT LABEL>: <PREVIOUS RIGHT>

Current:
<LEFT LABEL>: <CURRENT LEFT>
<RIGHT LABEL>: <CURRENT RIGHT>
Close: <CANDLE CLOSE> <QUOTE ASSET>

Candle closed: <UTC TIME>
Preset: <PRESET CODE> v<VERSION>
Calculation version: <CALCULATION VERSION>

Informational only — not financial advice.
```

## Test Notifications

An authenticated CSRF-protected request with a UUID idempotency key creates a `telegram_test` outbox job without a body. It is limited to three new requests per user per 15 minutes; an idempotent replay returns the original safe job. It requires a connected, non-degraded destination. `queued`, `sending`, `retrying`, `sent`, and `failed` describe provider-processing state, not device receipt.

## Price-Alert Notifications

The price-alert trigger transaction creates its immutable alert event and a `telegram_price_alert` outbox row. The worker formats the stored snapshot as a plain UTC message. A triggered alert is final regardless of sending, retrying, or failing delivery.

## Notification Outbox

Outbox jobs hold the owned user/destination reference, kind, idempotency key, immutable payload, status, attempts, claim/next-attempt timestamps, safe failure category, and provider message ID. `telegram_preset_signal` jobs also hold restricted `signal_event_id` and `signal_subscription_id` references and require both fields. The uniqueness scope is `(user_id, idempotency_key)` across notification kinds, with a partial `(user_id, signal_event_id)` uniqueness rule for preset-signal jobs. The user FK cascades deletion; the connection, signal-event, and signal-subscription FKs restrict deletion.

## Worker Claim, Send, Retry, and Recovery

The optional notification worker claims `telegram_test`, `telegram_price_alert`, and `telegram_preset_signal` jobs in short transactions using lock-safe claims, then releases the database lock before the network request. For preset-signal jobs it rechecks the outbox references, subscription ownership and active status, current delivery preference, event invalidation state, and current owned connected destination before contacting Telegram. Safety failures become terminal `failed` jobs with `signal_delivery_preference_disabled`, `signal_subscription_inactive`, `signal_event_invalidated`, `telegram_connection_unavailable`, or `notification_payload_invalid` as applicable. The signal dispatcher has its own `FOR UPDATE SKIP LOCKED` claims, bounded subscription pages, stale-claim requeue, database retry, expiry, and attempt limit; it never performs a provider request. Confirmed sends record the provider message ID. Telegram rate limits and known temporary failures move to `retrying` using bounded backoff; blocked/invalid destinations become `failed` and degrade the connection; missing configuration becomes `telegram_not_configured`. Timeouts and uncertain provider outcomes become `telegram_delivery_outcome_unknown` and are not retried. A later worker detects stale `processing` claims and terminally marks them with the same outcome-unknown code; it never requeues them because provider outcome is uncertain. The worker never creates another outbox row, and no queue broker is used.

## Delivery Status and User-Facing Meaning

`queued`, `sending`, and `retrying` mean the platform has not confirmed delivery. `sent` means Telegram accepted the send request, not that the device displayed it. `failed` is a safe terminal processing failure. Connection degradation maps to safe user-facing unavailable/degraded status rather than provider details.

## Disconnect and Provider-Failure Behavior

Disconnect prevents future delivery through that destination. Provider blocking, invalid chats, missing configuration, transport failure, and rate limiting are categorized safely and do not reveal Telegram internals. A failed Telegram send never changes a price alert or signal occurrence. Disabling the preference, disabling the subscription, disconnecting the destination, or invalidating the occurrence before a queued preset-signal send suppresses that provider request.

## Stored and Prohibited Telegram Data

Stored identity is limited to Telegram user ID, private chat ID, optional username, connection timestamps/status/reason, processed update ID/outcome, token hash/lifecycle, and provider message IDs. Raw link tokens, bot tokens, webhook secrets, user-supplied chat IDs, and provider payloads are neither returned nor logged.

## Not Supported

Groups, channels, multiple destinations, user-supplied chat IDs, webhooks, scheduled polling infrastructure, per-occurrence website delivery history, and additional notification channels are not implemented. Durable preset-signal fan-out, provider delivery, and browser preference controls remain separate layers.

## Verification Status

The latest full isolated E2E pass exercised linking, long polling, provider sends, retries, uncertain outcomes, and preset-signal simulator delivery. Real Telegram provider behavior, device receipt, production credentials, and deployment recovery remain unverified. Preset-signal provider delivery is Implemented and Verified only against the isolated simulator path.
