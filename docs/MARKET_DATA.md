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

Issue #48 persists only confirmed Binance Spot `1m` candles as canonical rows, alongside approved derived `1h` and `4h` rows. All boundaries are UTC: `1h` runs minute 00 through 59, and `4h` begins at 00:00, 04:00, 08:00, 12:00, 16:00, or 20:00. `open_time` is inclusive and `close_time` is exclusive; Binance's inclusive source close time remains separate on canonical rows.

Current-candle identity is `(supported_market_id, timeframe, open_time)`. Repeated identical closed input is harmless. A changed confirmed value creates a new current revision and marks the previous complete revision superseded; it is never overwritten in place. The persistence boundary uses exact `Decimal` and `NUMERIC(38,18)` values only.

## Timeframe Aggregation

The initial persistence scope is limited to `1h` and `4h`. A complete derived row requires exactly 60 or 240 consecutive current complete `1m` sources in the exact UTC window. Its open, high, low, close, volume, and trade count are calculated from those sources only. Its source fingerprint is the SHA-256 digest of the ordered `<candle id>:<revision>` tuple. Incomplete windows record observed source count and fingerprint when available, but never OHLCV values.

No empty-minute synthesis or forward fill is allowed. Aggregation scheduling and provider ingestion remain Issue #49 work; the shared live/historical calculation implementation remains a later strategy-core responsibility.

Issue #51 accepts only the current complete `1h` and `4h` values after they have been adapted outside its pure
calculation package. A strategy input series must be UTC, strictly ordered, contiguous at exact timeframe
boundaries, and from one supported market and timeframe. A correction requires a caller to discard incremental
state and rebuild from current complete candles; calculations never repair or overwrite candle data.

## Missing Source Candles

Do not silently invent market data.

If one or more source minutes are missing:

- Mark the aggregate as incomplete.
- Do not evaluate candle-close strategies from it.
- Schedule or record reconciliation.
- Expose the data-quality problem through metrics and concerns when persistent.

Any future rule that synthesizes empty candles must be explicitly approved and documented.

The persistence repository accepts an explicit bounded UTC range to compact missing current complete `1m` rows into ranges. It treats incomplete and invalid current rows as missing and never calls Binance or repairs a gap.

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

## Supported Spot Market Catalog

Issue #28 fixes the initial product catalog to Binance Spot, USDT quote asset, and exactly `BTCUSDT`,
`ETHUSDT`, `BNBUSDT`, `SOLUSDT`, and `XRPUSDT`. The canonical exchange and market identifiers are
`binance` and `spot`; provider symbols are uppercase while stream symbols are lowercase. This is a product
allowlist, not permission to ingest every Binance symbol.

The API seeds the five rows without guessed provider metadata. An explicit `market:sync` command uses one
centralized unauthenticated HTTPX client to request only those symbols from Binance Spot
`/api/v3/exchangeInfo`. Normal API startup does not contact Binance, and this issue adds neither WebSocket
ingestion nor automatic scheduling.

Only `symbol`, status, base/quote assets, Spot permission, and `PRICE_FILTER` minimum, maximum, and tick
are retained. Decimal strings are parsed as `Decimal` and stored as PostgreSQL `NUMERIC(38,18)`; no binary
floating point, full provider payload, private metadata, orders, balances, or account information is kept.
Zero minimum or maximum disables that bound, while a zero tick makes a market unavailable.

A market is ready for new alert creation only when it remains product-enabled, `trading`, freshly checked
within `MARKET_CATALOG_MAX_AGE_SECONDS` (default 86400), and has valid minimum, maximum, and positive tick
rules. Stale or disabled metadata remains stored but is unavailable for new alerts. The later alert API
must resolve this ready catalog record rather than trusting client exchange, market, or symbol strings.

If the provider response is malformed, incomplete, rate limited, unavailable, or cannot be persisted, the
sync rolls back and leaves the last valid catalog unchanged. A bounded single retry honors a numeric
`Retry-After`; there are no unbounded retries. `HALT`, `BREAK`, missing, and structurally unsupported
symbols are recorded with stable unavailable state and never activate an alert.

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

- Whether derived candles are persisted.
- Retention and partitioning.
- Scheduling mechanism.
- Market-data library versus a small internal client.
- Maximum acceptable data-freshness delay before alerts are suspended.

## Price Alert Creation Boundary

Issue #30 resolves price-alert creation through the controlled catalog rather than trusting arbitrary identifiers.
The market must be enabled, trading, fresh, complete, and have a positive tick. Plain `Decimal` targets are
validated against enabled minimum/maximum bounds and exact tick alignment. Creation performs no Binance request,
current-price lookup, stream subscription, or evaluation.
# Centralized Binance Spot Live Prices

Issue #31 adds a separately runnable Binance Spot aggregate-trade stream for the controlled, alert-creation-ready catalog only (initially at most BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, and XRPUSDT). It uses one combined `<lowercase-symbol>@aggTrade` public stream, normalizes valid messages to exact-decimal `PriceEvent` values, and does not expose provider payloads to alert logic.

Messages are accepted only when their wrapper and payload symbols agree, aggregate IDs and trade IDs are non-negative and ordered, price is finite and positive, and timestamps are within the ten-second freshness and two-second future-tolerance boundaries. Aggregate ID is the per-symbol order key: duplicates and older IDs are discarded; jumps are observable but accepted. The first accepted event for each symbol after reconnect is marked `observed_after_reconnect`.

The reader validates before adding to a bounded 10,000-event queue. Queue backpressure closes the connection and reconnects instead of silently discarding a valid event. The stream does not persist historical trades or backfill data.

## Price-Alert Evaluation Sink

Issue #32 adds the price-alert evaluator as the second ordered internal queue sink after durable market-state
recording. It consumes only validated, fresh aggregate-trade events and never contacts Binance independently or
stores raw ticks. Stream disconnection and stale state pause evaluation; they do not alter active-alert lifecycle.
The first fresh post-reconnect event may produce an observed crossing from the persisted prior relation, and the
immutable event records that reconnect observation.

## Browser Market-State Feedback

Issue #33 renders only the safe alert-read market-data summary. A stale or disconnected state explains that
evaluation is paused or resumes after reconnection; unavailable explains that the alert is not evaluated. The
browser does not infer freshness from its clock, subscribe to Binance, or expose current-price data.
# Binance candle ingestion and repair

Issue #49 extends the single Binance Spot market-stream connection with two streams per ready
allowlisted symbol: `@aggTrade` and `@kline_1m`. Only provider-confirmed closed (`x=true`)
one-minute klines enter persistence; open kline updates are ignored. The stream normalizes decimals
before strategy boundaries, persists canonical `1m` revisions, and builds UTC-aligned complete `1h`
and `4h` windows from current source rows. It has no indicator or signal-evaluation responsibility.

`market:candles-bootstrap` requests the bounded 150-day default history in chronological pages of at
most 1,000 minutes. `market:candles-reconcile` repairs only missing bounded ranges; the stream also
requests a six-hour recent repair at startup and no more often than every 900 seconds. REST uses the
public `/api/v3/klines` endpoint, one request at a time, 10-second timeouts, bounded retries, and
safe 429/418 handling. These commands are explicit operator actions and were not executed here.
