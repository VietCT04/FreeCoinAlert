# Market Data

## Purpose and Supported Scope

FreeCoinAlert ingests public Binance Spot data for the controlled USDT catalog: `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, and `XRPUSDT`. Exchange and market type are fixed as `binance` and `spot`. This document owns ingestion, candle quality, aggregation, repair, freshness, and retention; model details are in [DATABASE.md](DATABASE.md).

## Controlled Market Catalog

The product allowlist is seeded locally. `market:sync` fetches Spot `exchangeInfo` for only those symbols and retains symbol, trading state, base/quote assets, Spot permission, and `PRICE_FILTER` rules. A product-enabled market is ready only when it is trading, has complete positive rules, and metadata checked within `MARKET_CATALOG_MAX_AGE_SECONDS`. Product enablement and provider readiness are separate states. A failed or malformed synchronization rolls back without replacing the last valid catalog.

## Runtime Process and Ownership

`market-stream` is the only long-running market process. It owns PostgreSQL advisory lock `freecoinalert:market-stream:binance:spot`; a second owner exits without streaming. It refreshes the catalog, opens one Binance combined WebSocket carrying every ready symbol's `@aggTrade` and `@kline_1m` streams, and routes accepted events through ordered bounded queues. Durable market-state recording precedes price-alert evaluation; confirmed-candle persistence, aggregation, and preset evaluation use the candle path. A full queue is backpressure: the connection is closed and reconnected rather than silently dropping an event.

## Live Aggregate-Trade Flow

Aggregate trades are normalized to exact `Decimal` price events only when wrapper and payload symbols agree, IDs are non-negative and ordered, price is finite and positive, and event time is within `MARKET_EVENT_MAX_AGE_SECONDS` and the future tolerance. Aggregate ID is the per-symbol ordering key: duplicates and older IDs are dropped; gaps are observable but accepted. Latest accepted state is throttled into an operational snapshot. Raw trades are not persisted as history. The first accepted event after reconnect is marked as such.

## Closed One-Minute Kline Flow

Only Binance `x=true` one-minute klines enter canonical persistence; open updates are ignored. Provider close time remains the provider's inclusive millisecond while stored candle `close_time` is exclusive (`open_time + 1 minute`). REST kline requests also accept only consecutive, valid one-minute rows with possible OHLC and non-negative numeric values.

## Canonical Candle Semantics

Current candle identity is supported market, timeframe, and UTC open time. Values use `Decimal`/`NUMERIC(38,18)`. Identical confirmed input is idempotent. Changed confirmed input creates a new current revision and supersedes the earlier complete revision; it is never overwritten. Incomplete and invalid rows have no OHLCV values. Source fingerprints digest the ordered current source candle ID/revision pairs.

## Historical-Analysis Canonical Dataset Snapshots

Historical-analysis dataset preparation reads only current canonical `1h`/`4h` rows already stored in PostgreSQL. It selects the exact warm-up and start-inclusive/end-exclusive analysis window, accepts only current complete, fully valued, UTC-aligned and contiguous candles, and persists full OHLCV/trade/source metadata in immutable dataset rows. It does not call Binance, repair gaps, aggregate candles, or mutate live-ingestion state. Missing warm-up, gaps, incomplete/invalid rows, correction races, unavailable data, and oversized ranges become safe typed dataset outcomes; no partial snapshot is created.

The dataset keeps warm-up candles separate from the user-visible analysis range and records a deterministic `historical_dataset_fingerprint_v1` over the pinned run identity and snapshot values. A later revision, source change, deletion, non-current row, or value mismatch marks the dataset `stale`; it is not rebuilt under the same run. The dataset candle foreign key restricts canonical retention while the dataset remains retained, so cleanup is deferred to the historical-analysis worker/report boundary.

The pure historical-analysis engine consumes these immutable snapshot values only after dataset validation. It recalculates fixed SMA/RSI signals without querying Binance, repairing gaps, aggregating new candles, or reading mutable current rows. The engine is not part of live market ingestion and has no worker or process entry point.

The browser preset surface consumes only the server-provided supported-market catalogue and the confirmed candle-close signal snapshots. It does not request provider data directly, accept arbitrary symbols, or calculate indicators in the browser.

## UTC 1h and 4h Aggregation

`1h` windows begin at minute 00; `4h` windows begin at 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00 UTC. Each requires exactly 60 or 240 consecutive current complete `1m` candles. Open is first source open, close is last source close, high/low are extrema, volume and trade count are sums. Missing or nonconsecutive sources create an incomplete aggregate, never synthetic candles.

## Bootstrap

`market:candles-bootstrap` is an explicit one-shot, singleton-locked operator command. It reconciles up to `CANDLE_BOOTSTRAP_DAYS` (default 150; 35–180) using chronological pages of at most 1,000 minutes. It contacts Binance's public `/api/v3/klines` endpoint and writes through the same closed-candle boundary.

## Reconciliation and Gap Repair

`market:candles-reconcile` is an explicit one-shot command for a bounded lookback (default 24 hours; maximum 168). The stream additionally requests a six-hour recent reconciliation at startup and then no more frequently than every 900 seconds by default. Reconciliation finds missing current complete `1m` ranges, requests only those pages, and persists returned closed rows. It does not invent gaps. Bootstrap allows a maximum 180-day range. All these modes share the stream singleton lock.

## Corrections and Revisions

A changed confirmed candle revision rebuilds affected derived windows. Signal evaluator state is marked stale for correction rebuild; immutable signal events are not edited or deleted. Historical rebuild processing may add invalidation records instead of mutating an occurrence.

## Freshness and Safety States

Price events older than the configured maximum, too far in the future, malformed, unsupported, duplicate, or out of order are rejected. Stream disconnection or stale market state pauses price-alert evaluation without changing an active alert. Candle-symbol state becomes unsafe for stale, gapped, or error data, suspending preset signal creation. `CANDLE_WS_MAX_AGE_SECONDS` and `CANDLE_DATA_MAX_LAG_SECONDS` both default to 180 seconds.

## Retention and Cleanup

`CANDLE_RETENTION_DAYS` defaults to 180. The repository has a cleanup boundary that deletes old candle revisions; no scheduler is implemented. Current complete data is not replaced by retention cleanup.

## Provider Retry and Rate-Limit Behavior

REST kline calls use a ten-second timeout, one request at a time, and up to three attempts for network and server errors with bounded exponential backoff and jitter. A 429 retries once only with a numeric `Retry-After`; 418 becomes `binance_ip_banned`; malformed, invalid, and nonconsecutive responses fail safely. Catalog synchronization has one bounded retry when numeric `Retry-After` is supplied. There is no distributed limiter: coordination is process-local and relies on the singleton process.

## Configuration

| Setting | Default | Meaning |
| --- | --- | --- |
| `BINANCE_SPOT_BASE_URL` | `https://api.binance.com` | Public REST base URL. |
| `BINANCE_SPOT_WS_BASE_URL` | `wss://stream.binance.com:9443` | Public WebSocket base URL. |
| `MARKET_CATALOG_MAX_AGE_SECONDS` | `86400` | API alert/subscription catalog freshness requirement. The stream currently uses a hardcoded 24-hour maximum instead. |
| `MARKET_EVENT_MAX_AGE_SECONDS` / `MARKET_EVENT_FUTURE_TOLERANCE_SECONDS` | `10` / `2` | Aggregate-trade time acceptance window. |
| `MARKET_CATALOG_REFRESH_SECONDS` / `MARKET_STATE_WRITE_INTERVAL_SECONDS` | `21600` / `1` | Stream catalog refresh and snapshot write cadence. |
| `MARKET_STREAM_RECONNECT_MAX_SECONDS` | `30` | Reconnect backoff cap. |
| `CANDLE_*` settings | See [OPERATIONS.md](OPERATIONS.md) | Candle freshness, bootstrap, repair, and retention bounds. |

## Failure Handling and Recovery

For stale data, inspect the market-symbol and candle-symbol operational state, restore the singleton stream, then run only the applicable explicit reconciliation command. For gaps, use the bounded reconciliation command; for a failed large history load, restart the explicit bootstrap within its bound. A 418 or persistent 429 requires stopping aggressive retries and reviewing provider limits. None of these paths have been runtime-verified.

## Not Supported

Futures, other exchanges, arbitrary symbols, raw-trade history, synthetic missing candles, intrabar indicator inputs, per-user provider connections, and automatic scheduled cleanup are not implemented.

## Verification Status

Implemented code and configuration were inspected statically. Provider connections, streams, repair, bootstrap, retention, and production behavior are unverified.
