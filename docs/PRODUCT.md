# Product

## Purpose

This document defines what FreeCoinAlert is, who it serves, what the MVP includes, and what it intentionally does not do.

## Product Summary

FreeCoinAlert is a web application that helps cryptocurrency users create market conditions and receive Telegram notifications when those conditions are met.

Users can:

- Connect a Telegram destination to their account.
- Subscribe to platform-provided signal templates.
- Create custom signals from supported indicators and operators.
- Select a supported Binance market, symbol, timeframe, evaluation mode, and cooldown.
- Pause, resume, update, or delete their alerts.
- Review triggered alert history and notification delivery state.

## Target Users

Initial users are retail cryptocurrency traders who want configurable alerts without keeping an exchange chart open continuously.

The MVP assumes users understand basic concepts such as trading pairs, timeframes, price thresholds, RSI, MACD, EMA, and volume.

## MVP Capabilities

### Account and Telegram

- Account registration and sign-in establish a secure browser session. The minimal browser flow provides registration, sign-in, session restoration after refresh, and current-session sign-out; it intentionally does not provide profile editing, recovery, verification, or a dashboard.
- Secure Telegram linking uses a short-lived, single-use token. Authenticated users can request
  a one-time deep link, view only their safe connection state, queue a test notification, and
  disconnect through the minimal root-route panel without entering a chat ID.
- One Telegram destination per user initially, unless a later issue expands this.
- The UI reports that a test notification is queued, pending, accepted by Telegram, or failed; it
  does not claim delivery to a user's device.

### Alerts

- One-time supported-market price-crossing alerts can be created from the authenticated root route after
  Telegram is connected. The first live price initializes crossing state; a later crossing can trigger one
  Telegram notification.
- Percentage price movement.
- RSI threshold.
- MACD crossover.
- EMA crossover.
- Volume spike.
- Platform-provided templates and validated custom rules.
- Alert lifecycle and Telegram-delivery state are shown separately; Telegram acceptance is not claimed as
  device delivery.

### Market Data

- Binance is the first exchange integration.
- The initial market catalog is Binance Spot with USDT-quoted `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, and `XRPUSDT` only.
- New alerts can use a symbol only after its provider price rules have been safely synchronized and remain fresh.
- One-minute closed candles are persisted as the canonical historical interval.
- Larger timeframes are derived internally.
- Real-time price events are used for immediate price alerts.
- A reconciliation job detects and repairs missing candle ranges.

## Product Boundaries

The initial product:

- Provides informational alerts only.
- Does not execute trades.
- Does not hold customer funds.
- Does not request or store customer Binance API keys.
- Does not provide portfolio management.
- Does not promise profit or guaranteed delivery.
- Does not allow users to execute arbitrary code.

## Future Capabilities

Possible later phases include:

- Historical strategy analysis and backtesting.
- Additional exchanges and markets.
- Additional notification channels.
- Intrabar indicator evaluation.
- Multiple Telegram destinations or group destinations.
- Paid plans and usage limits.

These are not MVP commitments until approved through GitHub Issues.

## Product Principles

- Alert semantics must be understandable before activation.
- Price alerts and candle-close indicator alerts must be clearly distinguished.
- Users must see the selected symbol, timeframe, evaluation mode, and cooldown.
- Duplicate prevention and delivery visibility are product requirements, not internal implementation details.
- Historical results must show assumptions, sample size, date range, fees, slippage, and strategy version.
- The application must not describe indicators as predictions or guarantee future performance.

## Initial Success Criteria

The MVP is successful when a user can:

1. Create an account.
2. Connect Telegram without manually entering a chat ID.
3. Create a supported alert.
4. Receive one correct notification when the condition triggers.
5. Avoid repeated notifications for the same trigger event.
6. View the alert and delivery in the web application.

## Pending Product Decisions

## Implemented Preset Signal Subscriptions

The platform exposes eight fixed, versioned indicator-signal presets for ready Binance Spot markets: SMA 200 price crosses above/below and RSI 14 crosses above 70/below 30, each on `1h` and `4h` confirmed candles. Users select only a market and an active preset version; formulas, inputs, periods, thresholds, directions, and timeframes remain server controlled. A user may keep up to 20 active subscriptions. Subscriptions are for the website signal feed and do not require Telegram. This slice creates neither calculations, occurrences, live feeds, nor delivery.

- Final product name and public domain.
- Maximum active alerts per user.
- Whether the MVP is permanently free or introduces paid limits later.
- Data-retention period for alert history and one-minute candles.
- Whether Telegram groups are supported in the first release.

## Implemented One-Time Price Alert API

Signed-in users with connected Telegram can create, list, read, and soft-delete only their own supported
one-time price-cross alerts. Targets are exact catalog-validated decimals, and each user has at most 20 active
alerts. Creation does not inspect the current price: the first accepted market event initializes state, and only
a later crossing can trigger. Live evaluation and Telegram delivery are not part of this API slice.
