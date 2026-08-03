# Product

## Purpose

FreeCoinAlert helps a signed-in user watch a controlled set of Binance Spot markets, create one-time price-crossing alerts, and subscribe to fixed indicator presets. It is an informational alert product, not a trading service.

## Current Product Summary

The current product has account sessions, private Telegram linking, a test-notification queue, a public supported-market catalogue, browser management for one-time price alerts, fixed preset subscription controls, inline Telegram-delivery controls, an authenticated historical/live signal feed, and an authenticated owner-scoped historical-analysis run API. Each signal subscription also stores an explicit owner-scoped Telegram-delivery preference and exposes dynamic Telegram readiness through the authenticated API. Historical-analysis runs persist bounded request snapshots and lifecycle metadata, an internal service can prepare canonical datasets with immutable candle snapshots, and a pure deterministic engine can produce an in-memory fixed-preset simulation result; no worker, report persistence, or frontend analysis flow exists yet. New live signal occurrences create one durable dispatch record; occurrence-time eligible subscriptions can produce at most one immutable-snapshot Telegram outbox job per user. The dispatcher does not call Telegram, while the notification worker performs the provider delivery with send-time safety checks. Browser and runtime/provider paths are implemented but unverified.

## Current User Journeys

- Register or sign in with an email address and password, restore the browser session, and sign out.
- Create a Telegram link, open its bot deep link, inspect connection state, disconnect it, and queue a Telegram test notification.
- View the controlled market catalogue and create, list, inspect, and delete a one-time price-crossing alert.
- Browse fixed signal presets, create/list/disable a subscription for an available market and preset version, and view the matching historical signal feed.
- Request, list, inspect, and cancel a bounded historical-analysis run for an available market and fixed preset version through the authenticated API; only safe lifecycle metadata is available.
- Read and change the per-subscription Telegram-delivery preference through the authenticated API and inline preset-card controls; enabling requires an active subscription and a connected, non-degraded Telegram destination, and the preference is disabled by default.
- Filter loaded signal history, receive matching live events while the page is visible, recover missed entries after reconnect or visibility changes, and optionally activate a short in-page sound.

The authenticated root order is account summary, Telegram connection, price alerts, then `Preset signals`. The section describes fixed technical signals as informational and not trading advice. Cards show the server-provided name, description, timeframe, confirmed candle-close input, fixed parameters, subscription state, Telegram preference, and destination readiness; formulas and parameters are not editable. Enabling Telegram delivery uses inline confirmation and a successful server response; disabling is direct, and unavailable readiness does not automatically clear an enabled preference. `Signal history` uses the wording that recent occurrences may predate the user's subscription, supports load-more pagination and lightweight market/preset filters, and keeps history visibility separate from Telegram delivery.

Live events are highlighted with visible `New live signal` text for five seconds only when a genuinely new event arrives while the page is visible. Replay, pagination, refresh, invalidation, and visibility-recovery entries do not receive the live highlight or sound. Sound is off by default, requires a user gesture to activate the session, and is generated locally as a short 880 Hz sine pip at a maximum gain of 0.08 for 120 ms. Mute persists only the safe boolean preference, suspends the audio context where possible, and never disables visual updates.

## Supported Markets and Signal Types

The controlled Binance Spot symbols are `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, and `XRPUSDT`. Availability depends on current validated catalogue metadata.

One-time alerts fire once when a live aggregate-trade price crosses a user-selected exact-decimal target. A preset signal is a global occurrence evaluated only from complete closed `1h` or `4h` candles:

- Price close crossing above or below SMA 200.
- Wilder RSI 14 crossing above 70 or below 30.

Each combination has version `1`: four SMA presets and four RSI presets across `1h` and `4h`. Preset parameters, formulas, timeframes, directions, and versions are read-only in the browser. A signal occurrence, authenticated API feed visibility, website UI, optional sound playback, Telegram-delivery preference, fan-out dispatch, outbox job, and Telegram provider delivery are separate concepts. Fan-out does not deliver backfilled history, and provider delivery rechecks consent, subscription, occurrence, and destination state before sending.

## User-Visible Status and Failure Semantics

Price alerts are `active`, `triggered`, `disabled`, or `failed`. They expose whether evaluation is ready, the latest observed price, trigger details when triggered, market-data freshness, and separate delivery status. A Telegram connection is `not_connected`, `linking`, `connected`, `degraded`, or `disconnected`. A subscription is `active` or `disabled`. The subscription API reports Telegram-delivery readiness as `ready`, `linking`, `not_connected`, or `degraded`; readiness is dynamic and is not stored on the subscription.

An unavailable or stale catalogue cannot be used to create alerts or subscriptions. Authentication, ownership, validation, rate-limit, and provider-safe failure responses are defined in [API.md](API.md).

## Current Limits

Enforced limits include: 15–128 character passwords; a 7-day default session lifetime; 10 price-alert creations per user and 30 per IP per 15 minutes; 20 subscription enables per user and 40 per IP per 15 minutes; 30 subscription disables per user per 15 minutes; 30 Telegram-delivery preference mutations per user per 15 minutes; and 3 test notifications per user per 15 minutes. Maximum active price alerts per user: 20. Maximum active signal subscriptions per user: 20. Disabled subscription records are not subject to a separate record-count limit. Limits are process-local.

Historical-analysis endpoints add 10 creates per user and 30 per direct client IP per 15 minutes, 30 cancellations per user per 15 minutes, 120 configuration/list/detail reads per user per 15 minutes, and a maximum of 2 queued or running runs per user. These limits are process-local.

## Not Supported

FreeCoinAlert does not execute trades, hold funds, request exchange API keys, accept user-authored strategies, expose arbitrary timeframes, provide user-facing historical datasets, simulations, reports, or performance claims, provide mobile/system push notifications, or allow custom sounds. The historical-analysis run API records bounded owner-scoped requests and safe lifecycle metadata; the separate internal preparation service creates canonical datasets and the pure engine creates only in-memory hypothetical results for future worker use. The API, browser controls, durable fan-out, provider-worker delivery, and pure historical engine remain separate and do not guarantee delivery or profit. Browser sound is optional, off by default, and does not guarantee delivery. The product makes no profit or delivery guarantee.

## Future and Not Supported Capabilities

Canonical historical dataset preparation and the deterministic fixed-preset simulation engine are Implemented and Unverified. Worker execution, report persistence, charts, public/social feeds, and mobile/system push notifications are Planned or Not supported. The owner-scoped historical-analysis run request and lifecycle API is Implemented but Unverified. Any future capability requires an approved issue and must preserve the separation between signal occurrence, in-app visibility, sound, delivery preference, fan-out job, Telegram provider delivery, and hypothetical historical analysis.

## Product Safety and Financial-Information Boundary

Signals and price alerts are informational only. Indicators do not predict future prices; no result is financial advice. The product uses exact decimal values for market prices and records strategy versions so signal occurrences can be traced to their definition and triggering candle.

## Verification Status

The described code is implemented on the documented repository snapshot, but no maintainer-requested end-to-end, provider, browser, migration, or runtime verification pass has been performed.
