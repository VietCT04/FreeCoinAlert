# US-0004: Create a One-Time Cryptocurrency Price Alert

## User Story

As a signed-in user with Telegram connected, I want to create a price alert for a supported cryptocurrency, so that I receive a Telegram notification when its price crosses my chosen target.

## Context

US-0003 establishes Telegram as the first notification destination. The next product capability should deliver FreeCoinAlert’s core value through the simplest useful alert type before introducing technical indicators or custom strategies.

The first version should support one-time price-crossing alerts with clear ownership, validation, status, and delivery behavior.

## Acceptance Criteria

- [ ] A signed-in user with Telegram connected can create a price alert.
- [ ] The user can choose from supported markets and cryptocurrency symbols.
- [ ] The user can choose whether the price must cross above or below a target.
- [ ] The target price is validated before the alert is created.
- [ ] The website shows the alert’s symbol, market, condition, target price, status, and creation time.
- [ ] A user can view only their own alerts.
- [ ] A user can deactivate or delete their own pending alert.
- [ ] The system evaluates active alerts using current market data.
- [ ] The alert triggers only when the price crosses the target in the selected direction.
- [ ] One alert event and one notification job are created atomically when the alert triggers.
- [ ] A triggered one-time alert is not triggered again.
- [ ] The Telegram notification clearly shows the symbol, target, trigger price, direction, and trigger time.
- [ ] The website shows whether the alert is active, triggered, disabled, or failed.
- [ ] Telegram delivery failure does not cause the alert condition to trigger repeatedly.
- [ ] Relevant product, API, database, market-data, alert, Telegram, security, observability, and continuity documentation is updated.

## Out of Scope

- MACD, RSI, moving-average, or other indicator alerts
- Recurring alerts
- Percentage-change alerts
- User-defined strategy expressions
- Arbitrary customer code
- Backtesting
- Multiple notification channels
- Telegram groups or channels
- Editing a triggered alert
- Futures positions, order execution, or exchange API keys
- Full historical candle storage beyond what is required by the approved market-data solution
- Supporting every cryptocurrency or exchange immediately

## Risks

- Price-crossing semantics must prevent duplicate triggers during repeated or out-of-order market updates.
- Market-data interruptions must not silently produce false alerts.
- Alert state and notification creation must be committed atomically.
- Decimal precision must be handled consistently for different symbols.
- The initial supported market, symbols, price source, and evaluation frequency require explicit technical decisions.
- Delivery failure must remain separate from whether the alert condition was successfully triggered.

## Follow-up Issues

- #28 - Add supported Binance Spot market catalog
- #29 - Add one-time price alert persistence
- #30 - Implement authenticated one-time price alert API
- #31 - Add centralized Binance live price stream
- #32 - Evaluate price crossings and queue Telegram alerts
- #33 - Add frontend one-time price alert flow

## Implementation Order

1. Complete US-0003 through Issues #19, #20, #21, #22, and #23.
2. Implement Issue #28.
3. Implement Issue #29.
4. Implement Issue #30.
5. Implement Issue #31.
6. Implement Issue #32.
7. Implement Issue #33.

Each implementation issue requires an explicitly approved solution comment before implementation begins.
