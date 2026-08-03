# US-0008: Analyze Historical Performance of Fixed Presets

## User Story

As a user, I want to analyze how a fixed signal preset performed historically on a supported market and date range, so that I can understand its past behavior and limitations before deciding how to use or subscribe to it.

## Context

FreeCoinAlert already has the foundations required for reproducible historical analysis:

- A controlled Binance Spot market catalogue.
- Canonical revisioned closed candles with UTC-aligned `1h` and `4h` windows.
- Fixed immutable-in-meaning preset versions.
- Provider-neutral Decimal implementations of SMA 200 and Wilder RSI 14.
- Equality-aware crossing semantics used by live signal evaluation.
- Immutable signal occurrences and explicit separation between calculation, visibility, notification, and delivery.

The product currently has no historical-analysis API, dataset snapshot, simulator, job runner, stored report, or browser report. Historical performance must therefore be introduced as a separate bounded informational workflow. It must not modify live evaluation, call Binance per user request, execute trades, or imply that historical results predict future performance.

## Acceptance Criteria

- [ ] An authenticated user can request historical analysis for one controlled supported market, one fixed preset code/version, and one explicit UTC date range.
- [ ] Preset formulas, parameters, timeframe, direction, calculation version, and simulation model are server controlled and versioned.
- [ ] Historical analysis uses canonical stored platform candles and never performs a customer-specific Binance request.
- [ ] Required warm-up data is validated separately from the user-visible analysis period.
- [ ] Only complete, positive, finite, strictly ordered, contiguous canonical candles aligned to the preset timeframe are accepted.
- [ ] Every result identifies the market, preset version, calculation version, simulation version, requested range, effective data range, candle revisions or dataset fingerprint, coverage, and creation time.
- [ ] A candle gap, incomplete window, invalid row, insufficient warm-up, unsupported version, correction race, or stale dataset produces an explicit safe outcome rather than a partial or silently repaired result.
- [ ] The simulation uses the same SMA 200, Wilder RSI 14, and crossing semantics as live fixed-preset evaluation.
- [ ] The simulation prevents look-ahead bias by defining when a signal becomes known and which later price can be used for hypothetical execution.
- [ ] Entry, exit, position sizing, initial notional, maximum holding period, fee, slippage, and end-of-range treatment are explicit, server controlled, versioned, and disclosed.
- [ ] The same immutable market, preset, dataset, assumptions, and engine version produce the same logical analysis result.
- [ ] Results include at least sample/trade count, gross return, net return, maximum drawdown, win rate, and profit factor, with safe handling of zero-trade and undefined metrics.
- [ ] Results include bounded hypothetical trade details and equity progression sufficient to explain the summary metrics.
- [ ] Warm-up observations do not count as user-visible trades or performance within the requested range.
- [ ] Historical analysis runs outside normal HTTP request processing and does not block or mutate live market ingestion.
- [ ] Users can view only their own requests and reports; authorization is enforced server-side.
- [ ] Repeated idempotent requests, worker retries, restarts, and repeated reads do not create duplicate logical runs or reports.
- [ ] Run creation, execution, progress, cancellation, retention, concurrency, date range, result size, and request frequency are bounded.
- [ ] Loading, queued, running, cancelling, cancelled, succeeded, failed, insufficient-data, stale-data, zero-trade, rate-limited, stale-session, and unavailable states are communicated safely where user-facing.
- [ ] Historical analysis does not create live signal occurrences, alerts, subscriptions, Telegram jobs, browser notifications, or trading actions.
- [ ] Reports clearly distinguish historical hypothetical simulation from live signal occurrence and actual provider delivery.
- [ ] Reports disclose data coverage, assumptions, fees, slippage, sample size, versions, limitations, and that results are not financial advice, predictions, or guarantees.
- [ ] Bot tokens, exchange credentials, raw provider responses, internal user IDs, and unnecessary personal data are not stored in reports or exposed to clients or logs.
- [ ] Relevant product, API, database, architecture, security, market-data, strategy, alert, backtesting, operations, observability, README, concerns, and continuity documentation is updated with each implementation change.

## Analysis Principles

### Fixed and Versioned Scope

The first historical-analysis capability supports only the existing server-controlled fixed preset versions and controlled Binance Spot markets. Users select identity and date range, not formula code or indicator parameters.

### Canonical and Reproducible Data

The result must be tied to validated stored canonical candle revisions. Historical analysis must not depend on a provider response that can change between repeated user requests.

### No Look-Ahead

A hypothetical action can use only information that would have been available at that historical time. A candle-close signal cannot be filled using an earlier price from the same candle.

### Explicit Simulation Assumptions

A signal occurrence alone is not a trade or return. The product must define and disclose one versioned execution model before displaying performance metrics.

### Informational Safety

Historical results describe one hypothetical model over past data. They do not predict future prices, recommend a trade, prove profitability, or guarantee that an alert or Telegram message would have been delivered.

## Out of Scope

- User-authored strategies, expressions, or code
- Editable indicator periods, thresholds, timeframes, or directions
- Parameter optimization, grid search, or automated strategy selection
- Multi-preset ranking or recommendation
- Portfolio construction or multi-asset allocation
- Leverage, margin, derivatives, short-selling products, or exchange order execution
- Exchange API keys or user-specific exchange account data
- Per-request provider candle downloads
- Live paper trading or automated trading
- Public/social report sharing
- Scheduled recurring historical analyses
- Claims of expected return, financial advice, or guaranteed performance

## Risks

- Look-ahead bias can materially overstate results if signal timing and execution timing are not separated.
- Incomplete history, candle corrections, or revision races can make a report non-reproducible without an immutable dataset manifest.
- Fee, slippage, sizing, exit, and holding assumptions can dominate results and mislead users if hidden or mutable.
- Small samples, zero-trade periods, and undefined metrics can be presented deceptively without explicit handling.
- Large date ranges or concurrent runs can consume database, CPU, memory, and storage needed by live ingestion.
- Users may confuse historical simulation with a prediction, recommendation, live alert, or actual delivered notification.
- Future preset or calculation versions must not silently reinterpret a stored report.

## Follow-up Issues

- #79 — Add owner-scoped historical analysis runs and API
- #80 — Build canonical historical-analysis dataset manifests
- #81 — Implement deterministic fixed-preset simulation engine
- #82 — Execute bounded analysis jobs and persist reports
- #83 — Add historical fixed-preset analysis flow and report

Implementation order:

```text
#79 → #80 → #81 → #82 → #83
```

Issue #83 should also follow the remaining US-0007 browser-control Issue #74 if that issue is still open, so the authenticated frontend is extended from the latest merged state.

Each implementation issue requires an explicitly approved technical solution comment before work begins.
