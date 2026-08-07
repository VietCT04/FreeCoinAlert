# US-0012: Visualize Historical Analysis Price Action

## User Story

As a user reviewing a historical analysis, I want to see the selected market's candles with the simulation's hypothetical buy and sell markers, so that I can understand when the strategy entered and exited relative to price movement.

## Context

The historical-analysis report currently presents server-provided metrics and equity progression, but it does not show the price action that produced the hypothetical trades. The chart must use the immutable candle dataset and trade records already captured by the report. It must remain clearly hypothetical: it does not display live prices, place orders, or imply that synthetic-short results are executable Binance Spot trades.

## Acceptance Criteria

- [ ] The report overview shows an interactive candlestick chart for the selected analysis range.
- [ ] The chart uses stored report candles and shows each available bounded preview candle's open, high, low, and close values.
- [ ] Hypothetical entry and exit markers are shown as buy or sell markers at their corresponding candles, including the inverse marker direction used by synthetic-short simulations.
- [ ] The chart clearly labels markers as hypothetical and explains the long and synthetic-short buy/sell meanings.
- [ ] Server-provided exact-decimal values remain safe for small prices such as `0.00002515`; browser conversion is limited to chart plotting and does not recalculate metrics or trades.
- [ ] The chart handles empty or invalid preview data, remains usable on narrow screens, and supports normal chart inspection such as scrolling and zooming.
- [ ] The report API, historical-analysis documentation, and E2E coverage describe the candle preview and marker semantics.

## Out of Scope

- Live market charts or WebSocket price updates.
- Real exchange order placement, order status, or portfolio tracking.
- User-created strategies, editable indicators, technical overlays, or chart drawing tools.
- Per-user Binance candle requests, client-side backtesting, or a full historical-data export.

## Risks

- Long analysis ranges can produce dense candles and overlapping markers; the browser preview must remain bounded and retain marker anchor candles.
- Synthetic-short markers can be misunderstood as executable Spot orders unless the legend and report disclosure remain visible.
- Exact decimal values must not be rounded into an unusable chart for low-priced assets.

## Follow-up Issues

- GitHub Issue: `#131`
