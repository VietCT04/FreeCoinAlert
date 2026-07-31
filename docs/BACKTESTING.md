# Historical Analysis and Backtesting

## Current Availability

No backtesting API, UI, job runner, trade simulator, stored result, profitability report, or historical-performance claim is implemented.

## Existing Compatibility Foundations

The platform stores canonical closed candles, derives UTC-aligned `1h`/`4h` candles, versions server-controlled preset calculations, and creates immutable signal occurrences. Calculation code is provider-neutral and is intended to preserve the same semantic result for the same complete contiguous history.

## Required Future Semantics

Future historical analysis must use stored platform data after coverage is validated, share the current strategy calculation contract, remain isolated from live ingestion, and make all input range and strategy-version choices explicit.

## Data and Strategy Version Requirements

Results must identify data source/coverage, exchange, market type, symbol, timeframe, UTC range, canonical candle revisions, preset and calculation version, and missing-data treatment. A published preset version must never be silently reinterpreted.

## Bias and Execution Assumptions

A future simulator must prevent look-ahead bias and define entry timing, execution price, exit, stop loss, take profit, duration, fees, slippage, sizing, and treatment of gaps/corrections. A signal alone is not a win-rate or profit claim.

## Required Result Disclosure

Any future presentation must disclose assumptions, date range, sample size, fees, slippage, strategy version, data source, and limitations, and must not present analysis as financial advice or a guarantee.

## Explicitly Not Implemented

Historical strategy reports, optimizers, customer-specific Binance queries, automated trading, profitability claims, and result persistence are not implemented.
