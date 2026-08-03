# Historical Analysis and Backtesting

## Current Availability

The authenticated owner-scoped historical-analysis run API, canonical dataset-manifest persistence, and pure deterministic fixed-preset simulation engine are Implemented but Unverified. The API stores a bounded request snapshot and lifecycle metadata for queued, running, succeeded, failed, or cancelled work. An internal database-facing preparation service validates canonical coverage and persists one ready/failed dataset plus immutable candle snapshots per run. The pure engine consumes equivalent immutable manifest/snapshot inputs and produces an in-memory result; no worker invokes either boundary, no result is persisted, and no browser analysis flow exists.

## Current Run Contract

Run creation supports only controlled Binance Spot markets, active fixed preset code/version pairs, `1h` and `4h` preset timeframes, `historical_fixed_preset_v1`, `fixed_horizon_v1`, and explicit UTC start-inclusive/end-exclusive ranges of 7 through 90 days. The server resolves the SMA `sma_close_v1` or RSI `rsi_wilder_close_v1` calculation snapshot and the required 200- or 15-candle warm-up boundary. Dataset preparation then reads only current canonical rows for the exact `[warmup_start, analysis_end)` window, requires complete contiguous coverage, snapshots full values and source metadata, and stores a deterministic `historical_dataset_fingerprint_v1`. The visible analysis range remains distinct from warm-up data.

Users can create, list, inspect, and cancel only their own runs. Creation requires CSRF and a UUID idempotency key, uses bounded process-local rate limits, and allows at most two queued or running runs per user. A queued cancellation is immediate; a running cancellation is recorded for a future worker to acknowledge. Responses contain safe snapshots, progress, timestamps, and failure categories only. No run state creates live signal occurrences, alerts, subscriptions, Telegram jobs, browser notifications, or trading actions.

## Deterministic Fixed-Preset Simulation Engine

`freecoinalert_api.historical_analysis.engine` is a provider-neutral, database-independent pure module. It creates no SQLAlchemy session, file, process, thread, network call, worker, or log side effect. Its published versions are `historical_fixed_preset_v1` and `fixed_horizon_v1`; changing signal timing, execution, costs, sizing, holding period, overlap handling, formulas, or metrics requires a new version.

The engine accepts one ready dataset manifest, ordered immutable candle snapshots, one pinned preset snapshot, its pinned calculation version, and the explicit analysis range. It supports all eight version-1 SMA 200 and Wilder RSI 14 presets on `1h` and `4h`. It recalculates from the supplied candles rather than reusing `signal_events`, so the result is reproducible from the selected dataset.

The fixed-horizon assumptions are: 10,000 quote units of initial equity; a signal is known at the confirmed signal-candle close; entry is the next candle open; the entry candle is held as candle one of six; exit is the sixth held candle close; cross-above is long and cross-below is synthetic short; one position uses 100% of current equity; overlapping signals are ignored; entry and exit slippage are each 5 basis points adverse; fees are 10 basis points of allocated equity per side; there is no stop loss, take profit, or early exit; incomplete forward windows are not opened; later trades compound prior net closing equity; and synthetic-short net loss is capped at 100% of allocated equity. A synthetic short is analytical inverse exposure, not an executable Binance Spot trade and does not model borrowing, margin, funding, liquidation, leverage, or derivatives.

For a signal at candle index `i`, `entry_index = i + 1` and `exit_index = entry_index + 5`. The signal reads only data through `i.close_time`, entry reads only the next candle open, and exit reads only the sixth held candle close. Warm-up candles initialize the calculation and prior relation but cannot create signals, trades, or visible equity points. A signal is not opened unless both entry and exit are inside `[analysis_start, analysis_end)`. A scheduled exit at a candle close is processed before a new signal known at that same close, so the next candle may be eligible for a new entry.

The engine reuses `sma_close_v1`, `rsi_wilder_close_v1`, and the equality-aware crossing helper used by live evaluation. It validates market/timeframe identity, UTC boundaries, completeness, positive finite prices, exact continuity, revisions, source metadata, and resource limits before calculation. Typed outcomes are `success`, `insufficient_history`, `invalid_input`, `gap_detected`, `unsupported_preset`, `unsupported_calculation_version`, `unsupported_engine_version`, and `unsupported_assumption_version`; non-success outcomes contain no partial trades or equity series.

Successful results contain immutable hypothetical trades, one net mark-to-market equity point per visible analysis candle close, and summary metrics for signal/trade counts, gross and net return, maximum drawdown, win rate, and profit factor. Zero-trade ranges succeed with `win_rate` and `profit_factor` undefined as `no_trades`; profit factor is undefined as `no_losing_trades` when gains exist without losses and is zero when losses exist without gains. Displayed Decimal values are normalized strings quantized half-even to eight places. The result fingerprint uses `historical_simulation_result_v1` and includes the dataset fingerprint, pinned versions, range, assumptions, every trade, every equity point, and every summary/undefined reason. Result metadata states that the output is a historical hypothetical simulation, not financial advice, not a prediction, not a delivery or profit guarantee, and that synthetic short results are not executable Binance Spot trades.

## Existing Compatibility Foundations

The platform stores canonical closed candles, derives UTC-aligned `1h`/`4h` candles, versions server-controlled preset calculations, and creates immutable signal occurrences. Calculation code is provider-neutral and is intended to preserve the same semantic result for the same complete contiguous history.

## Worker and Report Boundary

Future worker execution must call current-dataset validation immediately before simulation and again before report publication. It must pass immutable dataset rows to the pure engine after coverage is validated, remain isolated from live ingestion, and make all input range and strategy-version choices explicit. A stale dataset fails safely and is not rebuilt under the same run.

## Data and Strategy Version Requirements

Results must identify data source/coverage, exchange, market type, symbol, timeframe, UTC range, canonical candle revisions, preset and calculation version, and missing-data treatment. A published preset version must never be silently reinterpreted.

## Bias and Execution Assumptions

A future simulator must prevent look-ahead bias and define entry timing, execution price, exit, stop loss, take profit, duration, fees, slippage, sizing, and treatment of gaps/corrections. A signal alone is not a win-rate or profit claim.

## Required Result Disclosure

Any future presentation must disclose assumptions, date range, sample size, fees, slippage, strategy version, data source, and limitations, and must not present analysis as financial advice or a guarantee.

## Explicitly Not Implemented

Strategy reports, worker processing, optimizers, customer-specific Binance queries, automated trading, profitability claims, and report/result persistence are not implemented. The dataset preparation service and pure engine have no process entry point or worker consumer yet. Terminal-run and dataset retention remain unresolved until the worker/report boundary defines bounded cleanup; active runs and referenced datasets must not be removed automatically.
