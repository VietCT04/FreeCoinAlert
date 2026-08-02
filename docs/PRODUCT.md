# Product

## Purpose

FreeCoinAlert helps a signed-in user watch a controlled set of Binance Spot markets, create one-time price-crossing alerts, and subscribe to fixed indicator presets. It is an informational alert product, not a trading service.

## Current Product Summary

The current product has account sessions, private Telegram linking, a test-notification queue, a public supported-market catalogue, browser management for one-time price alerts, and APIs for fixed preset subscriptions. Market processing creates global closed-candle signal occurrences; subscriptions do not create separate copies of those occurrences. Runtime/provider paths are implemented but unverified.

## Current User Journeys

- Register or sign in with an email address and password, restore the browser session, and sign out.
- Create a Telegram link, open its bot deep link, inspect connection state, disconnect it, and queue a Telegram test notification.
- View the controlled market catalogue and create, list, inspect, and delete a one-time price-crossing alert.
- Browse fixed signal presets and create, list, or disable a subscription for an available market and preset version. The current web interface does not yet expose preset subscription management.

## Supported Markets and Signal Types

The controlled Binance Spot symbols are `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, and `XRPUSDT`. Availability depends on current validated catalogue metadata.

One-time alerts fire once when a live aggregate-trade price crosses a user-selected exact-decimal target. A preset signal is a global occurrence evaluated only from complete closed `1h` or `4h` candles:

- Price close crossing above or below SMA 200.
- Wilder RSI 14 crossing above 70 or below 30.

Each combination has version `1`: four SMA presets and four RSI presets across `1h` and `4h`. A signal occurrence, authenticated API feed visibility, website UI, sound playback, and Telegram delivery are separate concepts. The historical/live feed API is being added by the active #53 change; the website does not yet expose preset controls or feed UI.

## User-Visible Status and Failure Semantics

Price alerts are `active`, `triggered`, `disabled`, or `failed`. They expose whether evaluation is ready, the latest observed price, trigger details when triggered, market-data freshness, and separate delivery status. A Telegram connection is `not_connected`, `linking`, `connected`, `degraded`, or `disconnected`. A subscription is `active` or `disabled`.

An unavailable or stale catalogue cannot be used to create alerts or subscriptions. Authentication, ownership, validation, rate-limit, and provider-safe failure responses are defined in [API.md](API.md).

## Current Limits

Enforced limits include: 15–128 character passwords; a 7-day default session lifetime; 10 price-alert creations per user and 30 per IP per 15 minutes; 20 subscription enables per user and 40 per IP per 15 minutes; 30 disable operations per user per 15 minutes; and 3 test notifications per user per 15 minutes. Maximum active price alerts per user: 20. Maximum active signal subscriptions per user: 20. Disabled subscription records are not subject to a separate record-count limit. Limits are process-local.

## Not Supported

FreeCoinAlert does not execute trades, hold funds, request exchange API keys, accept user-authored strategies, expose arbitrary timeframes, provide backtesting or performance claims, or play notification sounds. It makes no profit or delivery guarantee. The website does not yet provide a signal-feed UI.

## Planned Capabilities

Frontend preset controls and browser notification sound are planned but unavailable. The authenticated historical/live signal-feed API is covered by the active #53 implementation; it is not yet available in merged `main`. See the runtime-domain documents for its current boundaries.

## Product Safety and Financial-Information Boundary

Signals and price alerts are informational only. Indicators do not predict future prices; no result is financial advice. The product uses exact decimal values for market prices and records strategy versions so signal occurrences can be traced to their definition and triggering candle.

## Verification Status

The described code is implemented on the documented repository snapshot, but no maintainer-requested end-to-end, provider, browser, migration, or runtime verification pass has been performed.
