# Strategies

## Purpose and Current Scope

The server owns fixed, versioned preset definitions and provider-neutral Decimal calculations over canonical complete candles. Users cannot choose parameters or submit expressions.

## Versioned Preset Catalog

Active seeded presets use close input and calculation version 1:

| Code | Public name | Version | Timeframe | Type | Parameters / direction | Calculation version |
| --- | --- | ---: | --- | --- | --- | --- |
| `price_sma_200_cross_above_1h` | Price crosses above SMA 200 | 1 | `1h` | `price_sma_cross` | period 200, above | `sma_close_v1` |
| `price_sma_200_cross_below_1h` | Price crosses below SMA 200 | 1 | `1h` | `price_sma_cross` | period 200, below | `sma_close_v1` |
| `rsi_14_cross_above_70_1h` | RSI 14 crosses above 70 | 1 | `1h` | `rsi_threshold_cross` | period 14, threshold 70, above | `rsi_wilder_close_v1` |
| `rsi_14_cross_below_30_1h` | RSI 14 crosses below 30 | 1 | `1h` | `rsi_threshold_cross` | period 14, threshold 30, below | `rsi_wilder_close_v1` |
| `price_sma_200_cross_above_4h` | Price crosses above SMA 200 | 1 | `4h` | `price_sma_cross` | period 200, above | `sma_close_v1` |
| `price_sma_200_cross_below_4h` | Price crosses below SMA 200 | 1 | `4h` | `price_sma_cross` | period 200, below | `sma_close_v1` |
| `rsi_14_cross_above_70_4h` | RSI 14 crosses above 70 | 1 | `4h` | `rsi_threshold_cross` | period 14, threshold 70, above | `rsi_wilder_close_v1` |
| `rsi_14_cross_below_30_4h` | RSI 14 crosses below 30 | 1 | `4h` | `rsi_threshold_cross` | period 14, threshold 30, below | `rsi_wilder_close_v1` |

Published preset parameters and formulas are server controlled and immutable for their version.

## Shared Calculation Contract

Calculations are shared by supported market, timeframe, strategy type, calculation version, period, and close input. This lets subscriptions reuse one calculation without changing their pinned preset meaning.

## Candle Input Requirements

Inputs are one market and one `1h` or `4h` timeframe, current complete candles, strictly ordered in UTC and contiguous at exact timeframe boundaries. Every close is finite and positive. Invalid identity, ordering, completeness, or a gap produces a typed `invalid_input` or `gap_detected` result.

## SMA 200 Version 1

`sma_close_v1` requires 200 confirmed closes. It sums exactly 200 Decimal closes, divides using the shared Decimal policy, and emits the SMA at each following confirmed candle. Incremental state retains 200 closes and a rolling sum; advancing removes the oldest close and adds the next.

## Wilder RSI 14 Version 1

`rsi_wilder_close_v1` requires 15 confirmed closes (14 changes). Initial average gain and loss are the arithmetic averages of the first 14 non-negative gains/losses. Later values use Wilder averaging: `(previous average * 13 + current gain or loss) / 14`. Equal gain/loss yields `50.00000000`; zero loss yields `100.00000000`; zero gain yields `0.00000000`. Other values are calculated at Decimal precision 50, half-even quantized to eight decimals, and bounded 0–100.

## Calculation Outcomes and Warm-Up

Results are `success`, `insufficient_history`, `invalid_input`, `gap_detected`, or `unsupported_version`. A signal evaluator records warming for a non-success calculation and emits no occurrence.

## Crossing Conditions

Price/SMA and RSI/threshold directions compare previous and current left/right values with equality-aware rules described in [ALERTS.md](ALERTS.md). The calculation produces values; the evaluator owns occurrence creation.

## Incremental and Batch Consistency

Batch series and incremental initialization/advance use the same candle validation, Decimal arithmetic, formulas, and calculation versions. They are required to produce the same semantic result for the same complete contiguous history.

## Candle Revision Behavior

The shared calculation key contains market, timeframe, strategy type, calculation version, period, and input. The evaluator's temporary cache identity combines that key with candle ID and revision. A revision makes the affected evaluator state stale and requires a rebuild; it does not mutate an immutable signal occurrence.

## Versioning and Historical Meaning

Signal events snapshot preset code/version, strategy type, calculation version, period, threshold, input, and values. A future preset version cannot silently change historical meaning.

The authenticated signal feed exposes that immutable snapshot through the user's matching subscription rows. Feed values retain canonical decimal strings, candle revision and UTC boundaries, occurrence/recording times, backfilled state, and safe invalidation status. The feed does not alter calculation semantics or create a per-user signal event.

The browser preset catalog renders these definitions read-only. It does not submit formulas, periods, thresholds, timeframe overrides, directions, or calculation versions; subscription requests identify only the canonical supported market and preset code/version.

## Unsupported Strategy Features

MACD, EMA, Bollinger Bands, volume spikes, configurable periods, combined rules, arbitrary user code, custom expressions, intrabar evaluation, and public report sharing are not implemented. The authenticated browser historical-analysis presentation exposes only reports produced by the fixed server-controlled worker and engine through a read-only guided flow and methodology tab; it does not expose formulas or editable parameters.

## Historical Simulation Compatibility

Historical-analysis dataset preparation supplies the pure engine with immutable snapshots of canonical complete `1h`/`4h` candles. SMA 200 uses exactly 200 warm-up candles and RSI 14 uses 15; the first visible analysis candle is outside the warm-up range. The engine recalculates from these rows with the same versioned calculations and equality-aware crossing helper used by live evaluation, preserves UTC ordering and completeness, and discloses the fixed simulation assumptions. The separate worker invokes it without calling Binance per user request, reusing stored `signal_events`, or reading mutable current candle rows after preparation. Successful output is persisted as an immutable owner-scoped report with complete trades and equity points; the browser presents server-provided metrics and series through a presentation-only equity chart without calculating or reinterpreting them.

The isolated E2E historical manifest pins each worker scenario to an existing preset code/version and fixed UTC range. Scenario assertions read the server's exact decimal and UTC strings, report undefined reasons, immutable fingerprints, and paginated sequence values; the browser never reproduces an indicator, trade, equity, or metric calculation.

## Verification Status

Implementations were inspected statically, and the named fixed-preset historical scenarios passed through the real worker in the isolated E2E suite. Numeric equivalence, incremental execution, and production historical/live runs remain unverified.
