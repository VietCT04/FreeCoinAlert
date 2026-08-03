# Historical Analysis and Backtesting

## Current Availability

The authenticated owner-scoped historical-analysis run API and canonical dataset-manifest persistence are Implemented but Unverified. The API stores a bounded request snapshot and lifecycle metadata for queued, running, succeeded, failed, or cancelled work. An internal database-facing preparation service now validates canonical coverage and persists one ready/failed dataset plus immutable candle snapshots per run; no worker invokes it yet, and it does not calculate indicators, simulate trades, persist a report, or provide a browser analysis flow.

## Current Run Contract

Run creation supports only controlled Binance Spot markets, active fixed preset code/version pairs, `1h` and `4h` preset timeframes, `historical_fixed_preset_v1`, `fixed_horizon_v1`, and explicit UTC start-inclusive/end-exclusive ranges of 7 through 90 days. The server resolves the SMA `sma_close_v1` or RSI `rsi_wilder_close_v1` calculation snapshot and the required 200- or 15-candle warm-up boundary. Dataset preparation then reads only current canonical rows for the exact `[warmup_start, analysis_end)` window, requires complete contiguous coverage, snapshots full values and source metadata, and stores a deterministic `historical_dataset_fingerprint_v1`. The visible analysis range remains distinct from warm-up data.

Users can create, list, inspect, and cancel only their own runs. Creation requires CSRF and a UUID idempotency key, uses bounded process-local rate limits, and allows at most two queued or running runs per user. A queued cancellation is immediate; a running cancellation is recorded for a future worker to acknowledge. Responses contain safe snapshots, progress, timestamps, and failure categories only. No run state creates live signal occurrences, alerts, subscriptions, Telegram jobs, browser notifications, or trading actions.

## Existing Compatibility Foundations

The platform stores canonical closed candles, derives UTC-aligned `1h`/`4h` candles, versions server-controlled preset calculations, and creates immutable signal occurrences. Calculation code is provider-neutral and is intended to preserve the same semantic result for the same complete contiguous history.

## Required Future Semantics

Future historical analysis must call current-dataset validation immediately before simulation and again before report publication. It must use the immutable dataset rows after coverage is validated, share the current strategy calculation contract, remain isolated from live ingestion, and make all input range and strategy-version choices explicit. A stale dataset fails safely and is not rebuilt under the same run.

## Data and Strategy Version Requirements

Results must identify data source/coverage, exchange, market type, symbol, timeframe, UTC range, canonical candle revisions, preset and calculation version, and missing-data treatment. A published preset version must never be silently reinterpreted.

## Bias and Execution Assumptions

A future simulator must prevent look-ahead bias and define entry timing, execution price, exit, stop loss, take profit, duration, fees, slippage, sizing, and treatment of gaps/corrections. A signal alone is not a win-rate or profit claim.

## Required Result Disclosure

Any future presentation must disclose assumptions, date range, sample size, fees, slippage, strategy version, data source, and limitations, and must not present analysis as financial advice or a guarantee.

## Explicitly Not Implemented

Strategy reports, deterministic simulation execution, worker processing, optimizers, customer-specific Binance queries, automated trading, profitability claims, and report/result persistence are not implemented. The dataset preparation service has no process entry point and no worker consumer yet. Terminal-run and dataset retention remain unresolved until the worker/report boundary defines bounded cleanup; active runs and referenced datasets must not be removed automatically.
