# Market Data

## Purpose

This document defines how FreeCoinAlert consumes Binance market data, stores canonical candles, derives larger timeframes, repairs gaps, performs historical backfill, and avoids rate-limit problems.

## Source of Truth

Binance public market data is the first external source.

The application must keep one centralized exchange client layer. Individual users and alerts must not create their own Binance connections or REST clients.

## Live Data Sources

### Real-Time Price Events

Use a suitable Binance ticker or trade stream for alerts that must react immediately to price movement.

Examples:

- Price above or below a threshold
- Price crossing a threshold
- Short-window percentage movement when explicitly supported

### One-Minute Kline Events

Use Binance one-minute kline streams for candle ingestion.

Persist a candle only after Binance reports it as closed.

An in-progress candle may be used for a future explicitly documented intrabar feature, but it must not overwrite the canonical closed candle.

## Canonical Candle Model

Closed one-minute candles are the canonical stored interval.

All timestamps are stored in UTC.

Uniqueness must be equivalent to:

```text
(exchange, market_type, symbol, open_time)
```

Writes must be idempotent so reconnects, retries, and repeated events are harmless.

## Timeframe Aggregation

Larger timeframes are derived from one-minute candles using UTC-aligned boundaries.

Examples:

- `5m`: minute 00–04, 05–09, and so on
- `15m`: minute 00–14, 15–29, 30–44, 45–59
- `1h`: top of each UTC hour
- `4h`: 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00 UTC
- `1d`: 00:00 through 23:59 UTC

A derived candle is closed only after its timeframe boundary is complete and the required source minutes are available.

Live and historical aggregation must use the same implementation.

## Missing Source Candles

Do not silently invent market data.

If one or more source minutes are missing:

- Mark the aggregate as incomplete.
- Do not evaluate candle-close strategies from it.
- Schedule or record reconciliation.
- Expose the data-quality problem through metrics and concerns when persistent.

Any future rule that synthesizes empty candles must be explicitly approved and documented.

## Reconnection

The WebSocket client must:

- Detect disconnects and provider shutdown events.
- Reconnect using bounded exponential backoff with jitter.
- Resubscribe to required streams.
- Determine whether candle gaps occurred during downtime.
- Avoid duplicate event processing.
- Track the time of the last successfully received event.

## Daily Reconciliation

The daily job is a data-quality repair process, not the primary ingestion method.

For every supported symbol and required period, it should:

1. Determine the expected one-minute timestamps.
2. Query the database for missing timestamps or ranges.
3. Request only missing ranges from Binance REST.
4. Respect request weights, response headers, and retry guidance.
5. Upsert recovered closed candles.
6. Recheck continuity.
7. Record unresolved gaps and run outcome.

A complete previous day contains 1,440 one-minute candles per continuously traded symbol.

## Historical Backfill

Historical backfill is separate from reconciliation.

Use it when adding a supported symbol or preparing a historical-analysis range.

Requirements:

- Run independently from the real-time path.
- Use centralized rate limiting.
- Fetch bounded chunks.
- Resume safely after failure.
- Upsert idempotently.
- Validate continuity and candle ordering.
- Record source, date range, and completion state.
- Never delay live alert evaluation.

## Rate-Limit Handling

All REST usage must pass through one coordinated limiter.

Required behavior:

- Track request weight when exposed by Binance.
- Bound concurrency.
- Honor `Retry-After` or provider guidance.
- Use exponential backoff for temporary errors.
- Stop aggressive retries after HTTP 429.
- Treat HTTP 418 as a serious operational incident.
- Distinguish validation errors from temporary provider failures.

User actions must not cause unbounded direct Binance requests.

Future backtests should use stored data instead of calling Binance per request.

## Symbol Metadata

The system needs controlled metadata for:

- Supported exchange and market
- Symbol status
- Base and quote assets
- Price and quantity precision when relevant
- Available streams
- First and last stored candle
- Data-quality status

Do not expose or accept arbitrary strings as supported symbols without validation.

## Data Scope

Do not ingest every Binance symbol by default.

Start with an approved limited list or symbols required by active product templates. Expanding coverage requires a storage and rate-limit review.

## Required Metrics

At minimum, track:

- WebSocket connection state
- Time since last event
- Last closed candle stored per symbol
- Candle rows written
- Duplicate upserts
- Known missing ranges
- Reconciliation duration and outcome
- REST request count, weight, retries, and rate-limit responses
- Backfill progress

## Testing Expectations

Use deterministic fixtures for:

- Closed versus unfinished kline handling
- Duplicate events
- Reconnect gaps
- UTC aggregation boundaries
- Missing source candles
- Idempotent reconciliation
- Rate-limit backoff behavior

Unit tests must not depend on a live Binance connection.

## Pending Decisions

- Initial market type: Spot only or additional markets.
- Initial symbols.
- Whether derived candles are persisted.
- Retention and partitioning.
- Scheduling mechanism.
- Market-data library versus a small internal client.
- Maximum acceptable data-freshness delay before alerts are suspended.