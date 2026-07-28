# Backtesting

## Purpose

This document defines the boundaries and correctness requirements for future historical strategy analysis. Backtesting is not part of the initial alert-only MVP.

## Core Principle

Future analysis should use FreeCoinAlert's stored historical market data after the required range is available and validated.

Do not call Binance independently for every customer analysis request. Binance REST remains available for centralized ingestion, gap repair, and controlled backfill.

## Signal Versus Strategy

A signal such as `MACD crosses above its signal line` does not have a meaningful win rate by itself.

A complete historical strategy must define:

- Market and symbol
- Timeframe
- Long or short direction
- Signal version
- Entry timing and price
- Exit conditions
- Stop loss
- Take profit
- Maximum holding period
- Position sizing
- Fees
- Slippage
- Handling of overlapping signals
- Handling of missing data

Without these assumptions, performance metrics are misleading.

## Shared Strategy Logic

Historical analysis must use the same strategy-core implementation as live alerts for:

- Candle aggregation
- Indicators
- Conditions
- Crossovers
- Rule validation
- Strategy versions

Given the same closed-candle history, the live and historical evaluators must identify the same signal times.

## Look-Ahead Prevention

A signal confirmed at the close of a candle cannot execute using information from before that close.

A safe initial convention is:

- Calculate the signal after candle close.
- Enter at the next candle open, adjusted for slippage and fees.

Other execution models require explicit documentation and must use only information available at the simulated time.

Avoid:

- Using future candles to fill missing values.
- Selecting symbols based on future availability without acknowledging survivorship bias.
- Optimizing parameters and reporting results on the same period without separating evaluation data.
- Using today's template behavior when reproducing an older immutable version.

## Data Requirements

Before running analysis, confirm:

- Complete required candle range
- Expected UTC alignment
- No unresolved gaps that affect the strategy
- Warm-up history before the requested start date
- Correct exchange, market, symbol, and timeframe
- Stored source and ingestion metadata where needed

When data quality is insufficient, fail or return an explicit incomplete status. Do not silently fabricate candles.

## Execution Model

A future strategy request should define an execution model such as:

```text
Signal: MACD bullish crossover on closed 15m candle
Entry: Next 15m candle open
Exit: MACD bearish crossover, 2% stop loss, 4% take profit, or 48-candle timeout
Fee: 0.1% on entry and exit
Slippage: 0.05% on entry and exit
Position size: Fixed notional amount
```

If stop loss and take profit are both touched in the same candle, the engine needs a documented conservative or lower-timeframe resolution rule.

## Metrics

Candidate metrics include:

- Number of trades
- Winning and losing trades
- Win rate
- Total return
- Annualized return when appropriate
- Maximum drawdown
- Profit factor
- Average profit
- Average loss
- Expectancy
- Average holding duration
- Sharpe or another risk-adjusted metric when assumptions justify it

Do not highlight win rate alone.

## Result Metadata

Every result must include:

- Strategy and schema version
- Exchange, market, symbol, and timeframe
- Requested and effective date range
- Warm-up range
- Number of trades
- Entry and exit assumptions
- Fees and slippage
- Position sizing
- Data source and quality status
- Calculation version
- Creation timestamp

## Job Isolation

Historical calculations must not delay or starve:

- WebSocket ingestion
- Candle persistence
- Live alert evaluation
- Notification delivery

Run analysis as isolated jobs with bounded concurrency and resource limits.

## Reproducibility

Store enough information to reproduce a result:

- Normalized strategy definition
- Immutable strategy version
- Data range and data revision identifier when needed
- Engine version
- Numeric and rounding behavior
- All execution assumptions

Changing the engine or data should not silently alter an existing saved result.

## User Communication

Historical results must state:

- Past results do not guarantee future performance.
- Results depend on assumptions and data quality.
- Fees and slippage materially affect outcomes.
- A small sample is not reliable evidence.
- The application provides informational analysis, not financial advice.

## Testing Expectations

Prioritize deterministic scenarios for:

- No look-ahead entry
- Stop loss and take profit
- Same-candle ambiguity
- Fees and slippage
- Missing candles
- Warm-up handling
- Live signal and historical signal equivalence
- Drawdown and profit-factor calculation
- Immutable result metadata

## Pending Decisions

- Initial execution model options.
- Position-sizing models.
- Same-candle stop/take-profit rule.
- Analysis job limits and retention.
- Whether lower-timeframe data can resolve execution ambiguity.
- Parameter optimization, which should remain out of scope until basic analysis is correct.