# Market Data

## Purpose and Supported Scope

FreeCoinAlert ingests public Binance Spot data for the controlled USDT catalog: `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, and `XRPUSDT`. Exchange and market type are fixed as `binance` and `spot`. This document owns ingestion, candle quality, aggregation, repair, freshness, and retention; model details are in [DATABASE.md](DATABASE.md).

## Controlled Market Catalog

The product allowlist is seeded locally. `market:sync` fetches Spot `exchangeInfo` for only those symbols and retains symbol, trading state, base/quote assets, Spot permission, and `PRICE_FILTER` rules. A product-enabled market is ready only when it is trading, has complete positive rules, and metadata checked within `MARKET_CATALOG_MAX_AGE_SECONDS`. Product enablement and provider readiness are separate states. A failed or malformed synchronization rolls back without replacing the last valid catalog.

## Runtime Process and Ownership

`market-stream` is the only long-running market process. It owns PostgreSQL advisory lock `freecoinalert:market-stream:binance:spot`; a second owner exits without streaming. It refreshes the catalog, opens one Binance combined WebSocket carrying every ready symbol's `@aggTrade` and `@kline_1m` streams, and routes accepted events through ordered bounded queues. Durable market-state recording precedes price-alert evaluation; confirmed-candle persistence, aggregation, and preset evaluation use the candle path. A full queue is backpressure: the connection is closed and reconnected rather than silently dropping an event.

The isolated E2E overlay points both Binance REST and combined WebSocket traffic to `http://provider-simulator:9000` and `ws://provider-simulator:9000`. The simulator provides the fixed catalogue, klines, deterministic aggregate trades, open/closed one-minute klines, unavailable-market responses, and disconnect/reconnect controls without contacting Binance. The recovery journeys assert safe alert behavior across disconnect/reconnect and provider-unavailable boundaries; they do not claim that a stale or unavailable provider state is a production health guarantee. E2E mode uses a fixed UTC clock and a separate database; it is not a normal market-data provider or a substitute for production verification.

## Live Aggregate-Trade Flow

Aggregate trades are normalized to exact `Decimal` price events only when wrapper and payload symbols agree, IDs are non-negative and ordered, price is finite and positive, and event time is within `MARKET_EVENT_MAX_AGE_SECONDS` and the future tolerance. Aggregate ID is the per-symbol ordering key: duplicates and older IDs are dropped; gaps are observable but accepted. Latest accepted state is throttled into an operational snapshot. Raw trades are not persisted as history. The first accepted event after reconnect is marked as such.

## Closed One-Minute Kline Flow

Only Binance `x=true` one-minute klines enter canonical persistence; open updates are ignored. Provider close time remains the provider's inclusive millisecond while stored candle `close_time` is exclusive (`open_time + 1 minute`). REST kline requests also accept only consecutive, valid one-minute rows with possible OHLC and non-negative numeric values. Binance REST klines provide trade count but not first/last trade IDs, so those IDs remain null for REST-reconciled rows; closed WebSocket kline events populate them when supplied by the provider.

## `market_candles` Persistence Path

The `market_candles` table is not populated by FastAPI startup or by aggregate-trade events. Candle writes enter through `CandleIngestionService` from these paths:

| Trigger | Provider input | Persistence action |
| --- | --- | --- |
| Normal local initialization | Binance REST klines | The one-shot `candle-bootstrap-init` service runs after catalog synchronization and before `market-stream`; it fills missing rows in the configured bounded history. |
| Live market stream | A validated closed (`x=true`) Binance `@kline_1m` event | `market-stream` persists that one closed `1m` candle immediately. Open kline updates do not reach the persistence service. |
| Recent reconciliation | Binance REST klines for detected missing ranges | The stream requests a bounded recent repair during initial setup and on its maintenance interval; `market:candles-reconcile` and `market:candles-bootstrap` invoke the same gap-based writer explicitly. |

For each accepted closed `1m` candle, the service opens a database transaction and locks the current row for that market, timeframe, and UTC open time. If no current row exists, it inserts complete revision `1`. If all canonical values match the current row, the event is an idempotent no-op. If confirmed values differ, the current row is marked superseded and a new current revision is inserted; the earlier revision is retained. The source upsert never stores an unfinished candle.

After a changed `1m` source row, the service rebuilds the containing UTC `1h` and `4h` windows from current `1m` rows. A derived window becomes complete only when it has exactly 60 or 240 consecutive source rows. Missing or nonconsecutive sources produce a current incomplete row with no OHLCV values; no synthetic candle is created. A later complete rebuild can complete an existing incomplete derived row, while a changed complete derived result creates a new revision. Live changed source and complete derived rows are then sent to the confirmed-candle pipeline for candle state and preset evaluation.

## Canonical Candle Semantics

Current candle identity is supported market, timeframe, and UTC open time. Values use `Decimal`/`NUMERIC(38,18)`. Identical confirmed input is idempotent. Changed confirmed input creates a new current revision and supersedes the earlier complete revision; it is never overwritten. Incomplete and invalid rows have no OHLCV values. Source fingerprints digest the ordered current source candle ID/revision pairs.

## Historical-Analysis Canonical Dataset Snapshots

Historical-analysis dataset preparation reads only current canonical `1h`/`4h` rows already stored in PostgreSQL. It selects the exact warm-up and start-inclusive/end-exclusive analysis window, accepts only current complete, fully valued, UTC-aligned and contiguous candles, and persists full OHLCV/trade/source metadata in immutable dataset rows. It does not call Binance, repair gaps, aggregate candles, or mutate live-ingestion state. Missing warm-up, gaps, incomplete/invalid rows, correction races, unavailable data, and oversized ranges become safe typed dataset outcomes; no partial snapshot is created.

The dataset keeps warm-up candles separate from the user-visible analysis range and records a deterministic `historical_dataset_fingerprint_v1` over the pinned run identity and snapshot values. A later revision, source change, deletion, non-current row, or value mismatch marks the dataset `stale`; it is not rebuilt under the same run. The dataset candle foreign key restricts canonical retention while the dataset remains retained, and the explicit historical-analysis cleanup command removes terminal runs and their dependent snapshots/reports in bounded batches.

The pure historical-analysis engine consumes these immutable snapshot values only after dataset validation. It recalculates fixed SMA/RSI signals without querying Binance, repairing gaps, aggregating new candles, or reading mutable current rows. The engine is not part of live market ingestion; the separate historical-analysis worker owns execution, cancellation boundaries, and report publication.

The browser preset and historical-analysis surfaces consume only server-provided supported-market, fixed-preset, and report snapshots. They do not request provider data directly, accept arbitrary symbols or presets, or calculate indicators in the browser. Historical analysis uses the worker's stored canonical dataset rather than a browser or per-request provider query.

## UTC 1h and 4h Aggregation

`1h` windows begin at minute 00; `4h` windows begin at 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00 UTC. Each requires exactly 60 or 240 consecutive current complete `1m` candles. Open is first source open, close is last source close, high/low are extrema, volume and trade count are sums. Missing or nonconsecutive sources create an incomplete aggregate, never synthetic candles.

## Bootstrap

The normal local startup path invokes this as a separate one-shot service; it is not a FastAPI startup hook. Existing rows are used by the gap check, so initialization does not replay the full history on every restart.

`market:candles-bootstrap` is an explicit one-shot, singleton-locked operator command. It fills missing rows for up to `CANDLE_BOOTSTRAP_DAYS` (default 150 for direct-host use; 35–180) using chronological pages of at most 1,000 minutes. The Compose `market` profile runs this same gap-based module through `candle-bootstrap-init`, maps `LOCAL_CANDLE_BOOTSTRAP_DAYS` to `CANDLE_BOOTSTRAP_DAYS`, and defaults the local bounded range to 35 days. It contacts Binance's public `/api/v3/klines` endpoint and writes through the same closed-candle boundary.

The isolated E2E overlay disables `candle-bootstrap-init`. After migration and catalogue initialization, the guarded `e2e-seed` module inserts deterministic fixed-UTC, exact-decimal canonical history and derived `1h`/`4h` rows idempotently. The market stream and historical-analysis worker wait for seed completion so live and historical paths consume the same stored canonical data. No synthetic missing candle is created and no production provider is contacted.

## Reconciliation and Gap Repair

`market:candles-reconcile` is an explicit one-shot command for a bounded lookback (default 24 hours; maximum 168). The running stream calls the same function during its initial setup for a six-hour lookback before opening its first WebSocket connection, then its maintenance loop schedules another request no more frequently than `CANDLE_RECENT_RECONCILIATION_SECONDS` (900 seconds by default). Reconciliation finds only missing current complete `1m` ranges, requests those REST pages, and passes the returned closed rows through the same persistence and aggregation logic. It does not rewrite every existing candle or invent gaps. Bootstrap allows a maximum 180-day range. Direct maintenance acquires the market singleton lock; the running stream reuses the lock it already owns.

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
| E2E provider URLs | See [TESTING.md](TESTING.md) | E2E mode requires both Binance URLs to point exactly to `provider-simulator:9000`; the simulator is isolated and has no host port. |
| `MARKET_CATALOG_MAX_AGE_SECONDS` | `86400` | API alert/subscription catalog freshness requirement. The stream currently uses a hardcoded 24-hour maximum instead. |
| `MARKET_EVENT_MAX_AGE_SECONDS` / `MARKET_EVENT_FUTURE_TOLERANCE_SECONDS` | `10` / `2` | Aggregate-trade time acceptance window. |
| `MARKET_CATALOG_REFRESH_SECONDS` / `MARKET_STATE_WRITE_INTERVAL_SECONDS` | `21600` / `1` | Stream catalog refresh and snapshot write cadence. |
| `MARKET_STREAM_RECONNECT_MAX_SECONDS` | `30` | Reconnect backoff cap. |
| `CANDLE_*` settings / `LOCAL_CANDLE_BOOTSTRAP_DAYS` | See [OPERATIONS.md](OPERATIONS.md) | Candle freshness, bootstrap, repair, and retention bounds; the Compose market profile maps the local bootstrap setting into the API setting. |

## Failure Handling and Recovery

For stale data, inspect the market-symbol and candle-symbol operational state, restore the singleton stream, then run only the applicable explicit reconciliation command. For gaps, use the bounded reconciliation command; for a failed large history load, restart the explicit bootstrap within its bound. A 418 or persistent 429 requires stopping aggressive retries and reviewing provider limits. None of these paths have been runtime-verified.

## Not Supported

Futures, other exchanges, arbitrary symbols, raw-trade history, synthetic missing candles, intrabar indicator inputs, per-user provider connections, and automatic scheduled cleanup are not implemented.

## Verification Status

The maintainer-requested local startup pass exercised Binance catalogue synchronization, REST candle bootstrap, and market-stream startup; the latest full isolated E2E pass exercised the simulator-backed catalogue, canonical seed, market stream, and disconnect/reconnect selection paths. Binance gap repair, correction behavior, retention, and production behavior remain unverified.
