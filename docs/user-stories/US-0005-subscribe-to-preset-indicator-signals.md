# US-0005: Subscribe to Preset Indicator Signals

## User Story

As a signed-in user, I want to enable predefined indicator signals and view their historical and live notifications, so that I can understand how each signal behaves and notice new market events immediately while using the website.

## Context

US-0004 introduces user-created one-time price alerts.

The next MVP capability should provide predefined technical-analysis signals maintained by FreeCoinAlert, such as:

- Price crosses below the 200-period moving average
- Price crosses above the 200-period moving average
- RSI crosses below 30
- RSI crosses above 70

Users select from available signal presets rather than configuring indicator periods, formulas, or rule expressions.

Each preset includes a historical notification feed so users can review when the signal previously occurred. While the user is viewing the feed, new notifications appear automatically and play a short sound.

## Acceptance Criteria

- [ ] A signed-in user can view the available preset signals.
- [ ] Every preset clearly shows its name, description, symbol, timeframe, indicator parameters, and trigger condition.
- [ ] A user can enable or disable available presets for supported symbols.
- [ ] Users cannot change the formula or parameters of a preset.
- [ ] The system evaluates presets using confirmed, complete market data.
- [ ] Moving-average and indicator calculations use shared, versioned strategy logic.
- [ ] A signal occurrence creates one immutable signal event.
- [ ] Duplicate processing of the same candle does not create duplicate signal events.
- [ ] A user can view a chronological feed of past signal notifications.
- [ ] Each feed entry shows the symbol, preset, trigger values, timeframe, and occurrence time.
- [ ] The feed updates automatically when a new subscribed signal occurs.
- [ ] A new feed entry is visually highlighted while the user is viewing the page.
- [ ] A short notification sound plays when a new event arrives while the page is visible.
- [ ] Sound is enabled only after user interaction, according to browser autoplay restrictions.
- [ ] The user can mute or unmute in-app notification sounds.
- [ ] The sound preference is preserved safely in the browser.
- [ ] Historical feed loading and live updates do not produce duplicate entries.
- [ ] Live-feed disconnection is shown safely and reconnects automatically with bounded retries.
- [ ] In-app feed delivery remains separate from Telegram delivery.
- [ ] Relevant product, API, database, market-data, strategy, alert, frontend, observability, and continuity documentation is updated.

## Initial Presets

The exact initial list requires an approved technical solution, but the first version should remain small, such as:

- Price crosses above SMA 200
- Price crosses below SMA 200
- RSI 14 crosses above 70
- RSI 14 crosses below 30

## Out of Scope

- User-defined indicator periods
- Custom strategy expressions
- Combining several indicators into one rule
- Arbitrary customer code
- Backtesting
- Strategy profitability claims
- Trading or order execution
- Price or indicator charts
- Recurring notification configuration
- Mobile push notifications
- Multiple exchanges
- Futures markets
- Social or public signal sharing
- Preset administration UI
- User-uploaded notification sounds

## Risks

- Preset definitions must be versioned so historical events retain their original meaning.
- Candle gaps or incomplete aggregates must suspend evaluation rather than produce false signals.
- Historical and live calculations must use identical indicator logic.
- Live-feed reconnection must not duplicate events.
- Browser autoplay rules prevent sound before user interaction.
- High-frequency presets could overwhelm users, so the initial catalog should remain limited.
- Signal occurrence, website feed visibility, and Telegram delivery must remain separate states.

## Follow-up Issues

- #48 - Add canonical candle and timeframe persistence
- #49 - Add Binance candle ingestion, bootstrap, and reconciliation
- #50 - Add versioned preset catalog and user subscriptions
- #51 - Add shared SMA 200 and RSI 14 calculation core
- #52 - Evaluate preset strategies and persist signal events
- #53 - Add historical feed and live in-app event stream
- #54 - Add frontend preset subscriptions and live notification feed
