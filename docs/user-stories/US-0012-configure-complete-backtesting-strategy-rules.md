# US-0012: Configure Complete Backtesting Strategy Rules

## Status

Approved

## User Story

As a FreeCoinAlert user, I want to define complete entry and exit rules for a historical backtest, so that the simulation represents a complete trading strategy instead of only detecting an entry signal and applying a hidden fixed exit.

## Context

Historical analysis currently starts from a fixed preset signal such as `RSI crosses below 30`. That describes when a hypothetical position may be entered, but a complete strategy also needs an explicit rule for when the position closes.

The previous historical-analysis model uses server-controlled next-candle-open entry and a fixed six-candle holding period. This story keeps the existing fixed preset catalogue as the source of entry signals but replaces the hidden fixed exit for new runs with an explicit immutable strategy configuration.

A strategy becomes:

```text
Entry rule
+ direction
+ one or more exit rules
+ existing execution assumptions
= historical strategy simulation
```

## Primary User Experience

The historical-analysis configure flow becomes a guided strategy builder:

1. Market and timeframe
2. Entry rule
3. Direction
4. Exit rules
5. Simulation assumptions
6. Review and run

Example:

```text
Market: BTCUSDT
Timeframe: 4H
Direction: Long

Entry
RSI crosses below 30

Exit rules
Take profit: +6%
Indicator exit: RSI crosses below 20
Maximum holding period: 7 candles

Execution
Entry at next candle open
Fee: server-controlled
Slippage: server-controlled
One position at a time
```

The exact configuration shown on the review step is the configuration persisted with the run and used by the simulation engine.

## Entry Rule Requirements

Entry conditions continue to come from the controlled fixed-preset catalogue and its immutable preset version.

This story does not add arbitrary entry formulas or editable indicator definitions.

For the MVP introduced by this story:

- direction is explicitly shown as `Long`;
- only long simulations are supported;
- entry occurs using the existing next-candle-open execution assumption after a confirmed entry signal;
- the existing no-look-ahead semantics remain unchanged.

## Supported Exit Rules

A new run must contain at least one supported exit rule.

### Take Profit Percentage

Close when price reaches the configured gain relative to the hypothetical entry.

Example:

```text
Take profit: +6%
```

### Stop Loss Percentage

Close when price reaches the configured loss relative to the hypothetical entry.

Example:

```text
Stop loss: -3%
```

### Indicator Exit

Close when one approved fixed indicator condition becomes true on a confirmed candle.

Initial required example:

```text
RSI crosses below 20
```

The exact allowed indicator-exit vocabulary must be controlled and validated by the server. The browser must not accept arbitrary expressions.

### Maximum Holding Period

Close after a configured number of held candles if no earlier exit rule has closed the position.

Example:

```text
Maximum holding period: 7 candles
```

## Multiple Exit Rules

A strategy may contain multiple compatible exit rules.

Example:

```text
Entry: RSI crosses below 30
Take profit: +6%
Stop loss: -3%
Maximum holding period: 7 candles
```

The first triggered exit closes the position.

Only one position is open at a time. Entry signals that occur while a position is already open continue to follow the existing overlapping-signal behavior.

## Same-Candle Ambiguity

Historical OHLC candles do not reveal the exact intrabar sequence between high and low.

If multiple exit rules could have triggered within the same candle and their ordering cannot be known, the simulation must use a documented deterministic conservative rule.

For the approved MVP, priority is:

```text
1. Stop loss
2. Take profit
3. Indicator exit
4. Maximum holding period
```

Example:

```text
Entry: 100
Take profit: +6%
Stop loss: -5%
Candle high: 108
Candle low: 94
```

Both percentage levels are touched, but the simulation records the stop loss because the actual intrabar order is unknown.

This policy must be explicit in the report and versioned simulation semantics.

## Strategy Configuration Requirements

Each new analysis run stores an immutable versioned strategy configuration containing at least:

- fixed entry preset code and version;
- timeframe;
- long direction;
- ordered or normalized supported exit rules;
- exact rule values;
- strategy configuration version;
- existing server-controlled execution-assumption version.

Conceptually:

```json
{
  "entry": {
    "preset_code": "rsi_cross_below",
    "preset_version": "..."
  },
  "direction": "long",
  "exit_rules": [
    {
      "type": "take_profit_percent",
      "value": "6"
    },
    {
      "type": "indicator_cross",
      "indicator": "rsi",
      "direction": "below",
      "value": "20"
    },
    {
      "type": "max_holding_candles",
      "value": 7
    }
  ]
}
```

The final normalized schema is owned by the implementation issue and requires explicit technical approval.

The configuration must not be editable after the run is created.

## Validation Requirements

The server is authoritative for validation.

It must reject unsupported or unsafe configurations including:

- no exit rule;
- unsupported exit type;
- unsupported indicator condition;
- malformed or non-positive percentages;
- invalid candle count;
- duplicate rules where duplicates have no defined meaning;
- conflicting combinations that the engine cannot execute deterministically;
- unsupported direction.

The browser may provide immediate shape/range guidance but must not duplicate the simulation engine as a source of truth.

## Simulation Requirements

For every open hypothetical position, the engine evaluates configured exit rules against each subsequent candle using only information available at that point in historical time.

Conceptually:

```text
Entry signal confirmed
        ↓
Enter at next candle open
        ↓
For each later candle
        ↓
Stop loss triggered?
Take profit triggered?
Indicator exit triggered?
Maximum holding reached?
        ↓
First applicable exit closes position
        ↓
Apply existing fee/slippage model
        ↓
Persist trade and exit reason
```

The simulation must preserve:

- no look-ahead;
- exact-decimal calculations;
- existing fee and slippage semantics;
- one position at a time;
- existing handling of overlapping signals;
- deterministic dataset and result fingerprints;
- immutable reports;
- synthetic or unsupported trading semantics never being presented as executable behavior.

## Trade and Report Requirements

Every hypothetical trade must record why it exited.

Examples:

```text
Take profit
Stop loss
RSI crossed below 20
Maximum holding period
```

The report must preserve a machine-readable exit code as well as a safe human-readable label.

Reports must show the complete strategy used for the run, including:

- entry rule and preset version;
- long direction;
- every configured exit rule;
- entry timing;
- fee;
- slippage;
- sizing;
- overlapping-signal behavior;
- same-candle exit priority;
- strategy/configuration/simulation versions.

Where exact counts can be derived from immutable trades, the report may show a breakdown of exits by reason.

## Historical Compatibility

Existing historical-analysis runs created before this story must remain readable and reproducible.

They retain their original fixed six-candle exit semantics and must not be silently reinterpreted as a new configurable strategy.

The application should clearly label the legacy fixed-holding behavior when displaying those reports.

## Frontend Requirements

The historical-analysis configuration page must provide an accessible exit-rule builder.

Users can:

- choose the existing fixed entry preset;
- see long direction explicitly;
- add supported exit rule types;
- configure rule values;
- remove rules;
- see validation guidance;
- review the complete strategy before submitting.

Example presentation:

```text
Exit Rules

1. Take Profit
   When price increases by [ 6 ] %

2. Indicator Exit
   RSI crosses below [ 20 ]

3. Maximum Holding Period
   Close after [ 7 ] candles
```

The frontend must preserve existing shadcn design, responsive behavior, keyboard/focus behavior, exact-decimal handling, CSRF, ownership, idempotency, safe errors, processing lifecycle, and report navigation.

The browser must not recalculate indicators, exits, returns, drawdown, or equity.

## Security and Privacy Requirements

- Preserve existing opaque-cookie authentication and CSRF behavior.
- Preserve owner-scoped historical-analysis runs and reports.
- Do not store analysis configuration or result data in sensitive browser persistence.
- Do not expose internal errors, database identifiers, or unsupported provider details.
- Server validation remains authoritative.

## Out of Scope

- Short strategies
- Arbitrary formulas or executable user expressions
- Pine Script compatibility
- Editable custom indicators
- Strategy optimization or parameter sweeps
- Machine-learning strategy discovery
- Multiple simultaneous positions
- Portfolio backtesting
- Live trading or order execution
- Additional markets introduced solely for this story
- Export or public sharing

## Acceptance Criteria

- [ ] New historical-analysis runs require an explicit complete strategy configuration rather than relying on a hidden fixed exit.
- [ ] The entry rule continues to use a fixed preset/version.
- [ ] Long direction is explicit and is the only supported direction for this story.
- [ ] Users can configure take-profit percentage, stop-loss percentage, approved indicator exit, and maximum-holding-candle rules.
- [ ] A run contains at least one valid exit rule.
- [ ] Multiple compatible exit rules are supported and the first triggered rule closes the position.
- [ ] Same-candle ambiguity follows the documented conservative priority: SL → TP → indicator exit → max holding.
- [ ] New strategy configurations are immutable and versioned.
- [ ] Every trade records its exit reason.
- [ ] Reports show the complete strategy and execution assumptions that produced the result.
- [ ] Existing fixed-six-candle reports remain readable and retain their historical semantics.
- [ ] No browser-side simulation or metric calculation is introduced.
- [ ] Existing ownership, CSRF, idempotency, exact-decimal, no-look-ahead, fee/slippage, and immutable-report guarantees remain intact.
- [ ] Current-state product, API, database, backtesting, strategy, architecture, security, accessibility, observability, E2E coverage, README, concerns, and continuity documentation remain synchronized during implementation.

## Implementation Issues

- #135 — Add immutable configurable strategy-exit model and API contract
- #136 — Execute configurable exit rules in the historical simulation engine
- #137 — Add historical-analysis strategy rule builder
- #138 — Report configurable strategy rules and trade exit reasons

Implementation order:

```text
#135 → #136 → #137 → #138
```

Each issue requires an explicitly approved technical solution comment before implementation.

## Verification Boundary

Planning approval does not authorize migrations, database commands, simulation runs, services, providers, builds, tests, Playwright, browser interaction, linting, formatting checks, type checks, accessibility scans, documentation generators, or other verification commands. Those remain subject to explicit maintainer direction.