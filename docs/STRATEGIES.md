# Strategies

## Versioned preset catalog

Issue #50 introduces catalog persistence only, not indicator calculation. The initial immutable presets use confirmed-candle closes: `price_sma_cross` has fixed period 200 and no threshold; `rsi_threshold_cross` has fixed period 14 and a threshold of exactly 70 for cross-above or 30 for cross-below. Each has `1h` or `4h` timeframe. A changed meaning must be represented by a new version, never by modifying a published row. Active versions accept new subscriptions; superseded versions do not but existing active subscriptions continue; disabled versions stop future evaluation and disable their subscriptions when that operational transition is performed.

## Shared SMA and RSI calculation core

Issue #51 adds the pure calculation boundary used by future live and historical evaluation. It accepts only ordered, current complete `1h` or `4h` candle values through an immutable provider-neutral contract; it does not read a database, call Binance, inspect users or subscriptions, evaluate crossings, or persist signal events.

`sma_close_v1` uses the latest 200 consecutive close prices and returns each rolling SMA after the 200th candle. `rsi_wilder_close_v1` uses Wilder's 14-change initialization, so its first value requires 15 consecutive closes. SMA values and RSI gain/loss averages are quantized to 18 decimal places; RSI values are quantized to 8, using a local Decimal context of precision 50 and `ROUND_HALF_EVEN`. Flat RSI is exactly 50, gain-only is 100, and loss-only is 0. A changed formula, input, rounding, warm-up, or progression requires a new calculation version and preset version.

Each calculation shares the immutable key `supported_market_id + timeframe + strategy_type + calculation_version + period + close`. Direction and RSI threshold are intentionally excluded so paired presets share one indicator result. Missing, duplicate, unordered, mixed, incomplete, invalid, or non-contiguous candles return typed `invalid_input` or `gap_detected`; insufficient history returns `insufficient_history`. Corrections are rebuilt from a complete current series by Issue #52 rather than mutating calculation state.

## Purpose

This document defines platform signal templates, custom-rule definitions, supported calculation concepts, validation, deterministic evaluation, shared calculation, and strategy versioning.

## Terminology

- **Indicator**: a derived value such as RSI, EMA, MACD, or average volume.
- **Condition**: a comparison or crossing relationship between values.
- **Rule**: one condition or a logical composition of conditions.
- **Signal template**: a platform-published, reusable, versioned rule with user-facing metadata.
- **User alert**: a configured instance of a template or a validated custom rule for a symbol, timeframe, and destination.
- **Strategy**: in future historical analysis, a signal plus complete entry, execution, exit, risk, fee, and slippage assumptions.

A signal alone is not a complete trading strategy and does not have a meaningful win rate.

## Initial Indicators and Conditions

Candidate MVP support:

- Current price
- Percentage price change
- RSI
- EMA
- MACD line and signal line
- Candle volume
- Average volume

Candidate operators:

- Greater than
- Greater than or equal
- Less than
- Less than or equal
- Cross above
- Cross below
- Logical `AND`
- Logical `OR`

Exact support and parameter limits require focused issues and tests.

## Custom Rule Format

Users must not submit executable code.

Rules use a constrained, versioned JSON-compatible format.

Example:

```json
{
  "schemaVersion": 1,
  "type": "CROSS_ABOVE",
  "left": {
    "type": "MACD_LINE",
    "fastPeriod": 12,
    "slowPeriod": 26,
    "signalPeriod": 9
  },
  "right": {
    "type": "MACD_SIGNAL",
    "fastPeriod": 12,
    "slowPeriod": 26,
    "signalPeriod": 9
  }
}
```

The API must validate the complete rule before saving or activation.

## Validation

Validate:

- Schema version
- Supported node types
- Indicator parameter ranges
- Required relationships such as fast period less than slow period
- Rule depth
- Condition count
- Logical nesting
- Type compatibility between operands
- Supported timeframe and evaluation mode
- Maximum calculation complexity
- Numeric precision and threshold ranges

Reject unknown fields when doing so improves safety and compatibility.

## Evaluation Modes

### Real-Time Price

Used for immediate price conditions. The evaluator receives a current price event and relevant prior state.

### Candle Close

Used by default for indicators. The evaluator receives a completed candle sequence or updated deterministic indicator state.

Intrabar indicator evaluation must be introduced as a separate mode rather than silently changing candle-close behavior.

Issue #48 provides only the persistence boundary for future candle-close inputs. Strategy reads must use current, complete `1m`, `1h`, or `4h` rows ordered by UTC `open_time`; incomplete, invalid, and superseded rows are never valid inputs. No indicator calculation or preset evaluation is introduced by that issue.

## Deterministic Evaluation

Given the same:

- Strategy or rule version
- Ordered input candles or price events
- Prior evaluation state
- Numeric precision and rounding rules

The evaluator must produce the same result in live processing and historical analysis.

Avoid hidden dependencies on wall-clock time, provider ordering outside the stored sequence, or mutable platform defaults.

## Shared Strategy Core

The same package must provide:

- Candle aggregation
- Indicator calculations
- Condition evaluation
- Crossover behavior
- Logical composition
- Rule validation models
- Evaluation result models

Do not maintain separate MACD, RSI, or aggregation implementations for live alerts and historical analysis.

## Shared Calculations

Where practical, calculate a unique indicator combination once.

A calculation identity should include:

```text
exchange + market + symbol + timeframe + indicator + parameters
```

User conditions then evaluate against the shared value.

Sharing must not weaken isolation or correctness. Cache invalidation, ordering, and restart state need explicit design.

## Signal Templates

A template should include:

- Stable template identity
- Immutable version
- Name and description
- Rule definition
- Supported markets and timeframes
- Default parameters and cooldown
- Explanation of evaluation mode
- Publication status
- Creation timestamp

Existing user subscriptions remain pinned to the selected version.

Changing a template's behavior requires a new version. Do not silently modify historical meaning.

## Custom Rule Versioning

Store:

- Rule schema version
- Complete normalized rule definition
- Indicator and operator versions when algorithm changes would affect results
- Creation and update timestamps

When a user edits an active custom alert, the implementation must define whether it mutates the alert, creates a new alert version, or resets evaluation state.

## Numeric and Indicator Consistency

For every indicator, document and test:

- Input ordering
- Warm-up requirements
- Initialization method
- Missing-candle behavior
- Decimal or floating-point approach
- Rounding for display versus evaluation
- Equality semantics
- Reference fixture values

Do not select an indicator library without verifying that its live incremental and historical batch behavior are consistent.

## User-Facing Explanation

The alert builder must explain:

- What the condition means
- Timeframe
- Candle-close versus real-time evaluation
- Required warm-up when relevant
- Cooldown
- That indicators are informational and do not guarantee future movement

## Testing Expectations

Maintain deterministic fixtures for:

- RSI, EMA, MACD, and volume calculations
- Warm-up boundaries
- Cross above and cross below
- Equality cases
- Logical rule nesting
- Validation limits
- Live incremental versus historical batch equivalence
- Template-version pinning

## Pending Decisions

- Exact rule schema.
- Initial indicator set and parameter limits.
- Numeric precision and reference library.
- Rule depth and complexity limits.
- Custom alert edit/version behavior.
- Template publication and administration workflow.
# Candle availability boundary

Issue #49 provides confirmed canonical and derived candles only. It does not calculate SMA or RSI or
evaluate signals. The future preset evaluator must reject stale, gapped, or error candle states.
