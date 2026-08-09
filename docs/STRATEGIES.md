# Strategies

## Purpose and Current Scope

The server owns fixed, versioned entry-preset definitions and provider-neutral Decimal calculations over canonical complete candles. Historical-analysis runs additionally persist a versioned, server-validated exit strategy; users cannot submit formulas, expressions, or arbitrary indicator definitions.

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

MACD, EMA, Bollinger Bands, volume spikes, configurable indicator periods, arbitrary user code, custom expressions, intrabar evaluation, and public report sharing are not implemented. The authenticated browser historical-analysis presentation exposes only server-supported fixed entry presets and approved configurable exit controls; it does not accept formulas, arbitrary indicators, or client-side simulation logic.

## Historical-Analysis Strategy Contract

Each historical-analysis run stores an immutable `historical_strategy_snapshot_v1` with the fixed entry preset code/version, timeframe, signal direction, calculation version, position direction, and normalized exit rules. Omitted strategy input maps to `legacy_fixed_horizon_v1`: `cross_above` remains long, `cross_below` remains synthetic short, and the exit remains six candles. Explicit strategies use `configurable_exit_v1` and support long direction with at most one take-profit percentage, one stop-loss percentage, one RSI threshold-cross exit, and exactly one maximum-holding rule. The server publishes the supported rule types, limits, and same-candle priority through the historical-analysis configuration endpoint.

The RSI exit vocabulary is pinned to RSI 14, close input, the selected entry timeframe, and `rsi_wilder_close_v1`; the browser supplies only direction and threshold. TP, SL, and RSI values are validated as finite exact decimals and serialized as canonical strings. Rule order is normalized to stop loss, take profit, RSI threshold cross, then maximum holding. The SHA-256 strategy fingerprint is part of the owner-scoped idempotency identity. Configurable execution and trade exit semantics are implemented by the separate `historical_configurable_exit_v1` engine; this contract does not change the fixed engine.

## Historical Simulation Compatibility

Historical-analysis dataset preparation supplies the pure engines with immutable snapshots of canonical complete `1h`/`4h` candles. SMA 200 uses exactly 200 warm-up candles and RSI 14 uses 15; the first visible analysis candle is outside the warm-up range. Both paths recalculate from these rows with the same versioned calculations and equality-aware crossing helper used by live evaluation, preserve UTC ordering and completeness, and disclose their execution assumptions. The fixed path preserves six-candle long/synthetic-short behavior; the configurable path is long-only and evaluates its pinned stop-loss, take-profit, RSI-cross, and maximum-holding rules deterministically. The separate worker dispatches by the persisted simulation version without calling Binance per user request, reusing stored `signal_events`, or reading mutable current candle rows after preparation. Successful output is persisted as an immutable owner-scoped report with complete trades, exit metadata, and equity points; the browser presents server-provided metrics and series through presentation-only charts without calculating or reinterpreting them.

Published reports copy the immutable strategy snapshot and fingerprint from the run. Their server-persisted exit-reason counts cover the complete trade set, while trade rows and chart markers expose the exit reason, exact rule snapshot, and price basis without reconstructing them in the browser. Synthetic-short safety wording is conditional on the stored position direction; the long-only configurable path does not inherit that disclosure. A successful report may be converted to an existing live entry-signal subscription only when its exact preset code/version remains active; the conversion does not carry historical exits, position direction, or PnL into live behavior.

The isolated E2E historical manifest pins each worker scenario to an existing preset code/version and fixed UTC range. Scenario assertions read the server's exact decimal and UTC strings, strategy fingerprints, exit rules, persisted exit-reason counts, trade exit metadata, report undefined reasons, immutable fingerprints, and paginated sequence values; the browser never reproduces an indicator, trade, equity, exit count, or metric calculation.

## Verification Status

Implementations were inspected statically, and the named fixed-preset historical scenarios passed through the real worker in the isolated E2E suite. Numeric equivalence, incremental execution, and production historical/live runs remain unverified.
