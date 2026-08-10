# US-0014: Backtest Against the Latest Two Years of Market Data

## Status

Approved

## User Story

As a FreeCoinAlert user, I want to backtest a strategy across up to the latest two years of historical crypto data, so that I can evaluate the strategy across substantially different market conditions instead of only a short recent period.

## Context

Historical Analysis currently supports only a short bounded date range. That is insufficient for evaluating a strategy across multiple market regimes and also makes sparse entry conditions appear to have too little evidence.

Simply changing a browser date limit is not sufficient. FreeCoinAlert must maintain enough canonical historical candles locally before a user starts a backtest, and it must build that history without creating an unsafe volume of rate-limited Binance REST requests.

The approved architecture is:

```text
Binance public historical archives
        ↓
resumable bulk backfill primitives
        ↓
background candle-backfill worker
        ↓
canonical FreeCoinAlert candle database
        ↓
live ingestion + bounded gap reconciliation
        ↓
rolling two-year+ history
        ↓
Historical Analysis worker
        ↓
backtest from stored canonical data only
```

A user's backtest request must never directly trigger a Binance provider fetch.

Full long-range coverage is **not** an application-startup prerequisite. Web/API/core product functionality becomes usable while the historical backfill worker continues extending canonical coverage in the background.

## Product Range

Historical Analysis supports a maximum selected analysis window of exactly 730 complete UTC days.

The existing minimum range remains unchanged unless a focused implementation issue establishes a documented reason to change it.

The browser may provide convenient presets such as:

```text
30 days
90 days
6 months
1 year
2 years
Custom
```

The server remains authoritative for `minimumRangeDays`, `maximumRangeDays`, and actual available canonical coverage.

## Data Source Hierarchy

### Bulk Historical Data

Long-range bootstrap should use Binance's official public historical Spot kline archives rather than paginating the rate-limited REST kline endpoint across the entire two-year window.

For completed old periods:

```text
monthly archive
→ checksum verification
→ parse and normalize
→ canonical upsert
→ durable checkpoint
```

For completed days not yet represented by a monthly archive:

```text
daily archive
→ checksum verification
→ parse and normalize
→ canonical upsert
→ durable checkpoint
```

Archive ingestion must validate symbol, interval, timestamp semantics, payload shape, checksum, and canonical candle invariants before marking coverage complete.

### REST Reconciliation

Binance REST klines are a secondary source used only for bounded cases such as:

- the recent edge not yet present in public archives;
- small canonical gaps;
- archive-unavailable completed ranges where REST fallback is explicitly allowed;
- controlled repair/reconciliation.

REST must not be the primary two-year bootstrap mechanism.

### Live Data

The existing market stream continues owning live market ingestion and recent canonical candle updates.

This story does not replace live WebSocket ingestion with historical polling.

## Resumable Backfill

Historical ingestion must be durable and resumable.

Conceptually, FreeCoinAlert records enough checkpoint state to know:

- exchange;
- market type;
- symbol;
- source interval;
- source archive/range identity;
- covered range start/end;
- source/checksum identity;
- status;
- attempt count;
- completion time.

If a two-year bootstrap stops after importing many completed months, restarting the process must continue from missing/incomplete ranges rather than downloading those completed months again.

Imports must be idempotent against canonical candle uniqueness/revision semantics.

A corrupt, malformed, checksum-invalid, wrong-symbol, wrong-interval, or otherwise invalid archive must not produce a falsely complete canonical range.

## Background Backfill and Application Readiness

Deep historical coverage must run as a dedicated background process/service rather than as a required one-shot application-startup job.

The target runtime shape is:

```text
DB migrations + API + Web + market catalogue
                ↓
       application becomes usable
                ↓
market stream + bounded recent reconciliation
                ↓
long-range historical backfill worker
                ↓
coverage grows toward the 765-day target
```

The following are distinct states:

```text
application readiness
historical coverage readiness
```

Web/API/auth/Telegram/price-alert and other functions that do not require deep candle history must remain usable while background coverage is incomplete.

The market stream must not wait for the entire 765-day history before connecting to the live provider. It retains its existing bounded recent reconciliation/live-ingestion responsibilities.

Features that require historical data gate themselves on actual canonical coverage:

- live preset evaluation may remain in its safe `warming` state when indicator history is insufficient;
- Historical Analysis allows only a requested range whose analysis window plus warm-up is complete;
- an unavailable longer backtest fails fast / remains disabled rather than waiting for provider acquisition.

The backfill worker must be resource-bounded so archive parsing/database writes do not starve normal application traffic. Completed checkpoints and persistent PostgreSQL data are reused across worker/application restarts.

Backfill should prioritize newest contiguous missing history across the controlled symbols, progressing backward so shorter useful ranges become available before the entire two-year target is complete.

## Timestamp Normalization

The archive ingestion path must explicitly normalize Binance archive timestamps into FreeCoinAlert's canonical UTC timestamp representation.

The implementation must account for Binance's documented historical archive timestamp-unit rules, including the Spot archive timestamp-unit change affecting 2025+ data.

Timestamp-unit handling must be deterministic and source-contract driven rather than guessing from arbitrary values.

## Shared Binance REST Rate Budget

All Binance Spot REST market-data consumers must share one conservative request-weight budget rather than operating independent retry/sleep loops.

The shared policy must cover existing catalogue/reconciliation/bootstrap REST consumers as applicable.

It must:

- observe provider request-weight information when available;
- bound concurrency;
- throttle before exhausting provider limits;
- honor `Retry-After` on HTTP 429;
- stop rather than busy-retry when HTTP 418 indicates a provider/IP ban;
- use bounded retry/backoff with jitter for explicitly retryable transient failures;
- expose structured operational logs/metrics for throttling and provider failures.

Backtests already runnable from canonical data must not become unavailable merely because Binance REST reconciliation is temporarily degraded.

## Canonical Coverage Requirement

FreeCoinAlert must retain enough source history for:

```text
730-day maximum analysis window
+ maximum supported indicator warm-up
+ small operational buffer
```

With the current supported presets, the maximum warm-up is 200 candles on the 4h timeframe, or 800 hours (33 days 8 hours). The approved product retention target is therefore **765 complete UTC days**, which provides the 730-day analysis window, maximum current warm-up, and a small operational margin.

If future supported strategies require more warm-up, the invariant must be increased rather than silently truncating valid analysis.

The retention/cleanup path must never delete candles still required to satisfy the supported maximum backtest window and warm-up invariant.

For the controlled market catalogue, coverage is maintained incrementally:

```text
inspect canonical coverage
↓
identify missing ranges
↓
fill only missing ranges
↓
retain persistent coverage
```

Completed ranges are not repeatedly downloaded on every application or worker startup.

Coverage state should distinguish at least:

```text
backfilling
ready
degraded
```

and expose safe actual/target ranges and derived progress where needed by operations and the authenticated Historical Analysis UI.

## Backtesting Requirements

The historical-analysis server contract expands its maximum range from 90 days to 730 complete UTC days.

The request path remains:

```text
request
→ validate requested range
→ verify canonical coverage + warm-up
→ build immutable historical dataset
→ simulate locally
→ persist immutable report
```

The backtest worker must not call Binance because a user requested a date range and must not wait for the background backfill worker.

If canonical data required for the requested analysis range/warm-up is incomplete, the request/run must fail safely with a stable product-level coverage/range-unavailable category rather than silently fetching provider data or simulating incomplete history.

An already-covered shorter range remains runnable while deeper historical coverage is still backfilling.

The implementation must review fixed dataset/candle limits that were designed around the previous short range. The allowable load must be derived from:

```text
requested duration / timeframe
+ required warm-up
+ bounded strategy requirements
```

A full 730-day range is approximately:

```text
1h: 17,520 analysis candles
4h:  4,380 analysis candles
```

before warm-up.

Existing no-look-ahead, exact-decimal, immutable dataset/result fingerprint, fee/slippage, strategy-version, owner-scoping, and historical-report compatibility guarantees remain unchanged unless another explicitly approved story changes a specific simulation semantic.

## Historical Compatibility

Existing completed reports remain readable and retain their original immutable datasets, assumptions, fingerprints, and strategy/simulation semantics.

Increasing the maximum selectable range must not reinterpret or recompute historical reports.

## Web Requirements

The Historical Analysis period controls add convenient long-range presets while preserving custom date selection.

The browser must use server-provided capabilities and coverage rather than becoming another source of truth for range limits.

When available, the UI should show actual canonical coverage and background state for the selected market/timeframe, for example:

```text
Historical data · Backfilling 63%
Available: 2025-05-01 → 2026-08-09 UTC
Target:    2024-07-06 → 2026-08-09 UTC
```

Covered shorter presets remain usable. A preset whose full requested analysis range plus warm-up is not yet available remains disabled and must not be silently shortened.

As background coverage grows, longer presets become available without restarting the application.

Selecting a long range must never cause the browser to call Binance directly.

## Local Development

Local development must not require downloading approximately two years of history before `pnpm dev:all` becomes usable.

The database remains persistent across normal local restarts.

`pnpm dev:all` should start the background candle-backfill worker with the market profile, but local readiness should succeed once the core services are ready/running rather than waiting for 765-day coverage completion.

A fresh local environment therefore behaves like:

```text
pnpm dev:all
→ Web/API/market stream become usable
→ background historical backfill continues
→ unrelated features can be tested immediately
→ longer Historical Analysis ranges unlock as coverage grows
```

Deep-history acquisition must not require setting a blocking `LOCAL_CANDLE_BOOTSTRAP_DAYS=765`. Any retained local configuration for startup reconciliation must remain small/bounded and distinct from the background historical target.

If canonical history is already complete, worker maintenance skips completed ranges rather than re-downloading them.

## Storage and Performance

The implementation must review, not assume, the storage/index impact of retaining approximately two years of one-minute canonical candles across the controlled market catalogue.

The target is millions of canonical rows, which is expected and must be handled with appropriate existing/new indexes and bounded ingestion transactions.

Schema/index/partition changes should be made only when justified by measured/query-plan requirements in the implementation design.

The background importer must use bounded archive concurrency, bounded database chunks/transactions, and explicit yielding/pacing so the backfill does not monopolize PostgreSQL or application resources.

## Observability

Production-safe observability should make it possible to distinguish:

- archive download/import success;
- checksum/format failure;
- coverage gaps;
- resume/skipped-complete ranges;
- REST repair requests;
- request-weight pressure;
- provider 429 throttling;
- provider 418 ban state;
- canonical retained-range health;
- background backfill status/progress;
- unavailable backtest coverage;
- application readiness independently from historical-coverage readiness.

Logs must avoid excessive per-candle noise.

## Security and Safety

- Historical imports remain public market-data ingestion only.
- Do not expose provider/internal storage details through unsafe user-facing errors.
- Preserve current authentication, CSRF, and owner scoping for Historical Analysis.
- Do not allow browser/user input to construct arbitrary provider URLs.
- Archive downloads/checksums/ranges must be derived from controlled market/interval configuration.
- Do not weaken existing canonical candle validation/freshness rules for live data.

## Out of Scope

- Backtesting beyond 730 selected days
- Arbitrary user-defined symbols or exchanges
- Futures historical data
- Portfolio backtesting
- Provider fetches initiated per user backtest
- Downloading the full two-year history on every startup
- Blocking Web/API/application readiness on full two-year history
- Replacing WebSocket live ingestion with polling
- Public user-generated datasets
- Paid third-party historical-data providers
- Strategy optimization/parameter sweeps introduced solely by this story
- Live trading or order execution

## Acceptance Criteria

- [ ] Historical Analysis supports a maximum selected range of 730 complete UTC days.
- [ ] The server remains authoritative for date-range validation.
- [ ] Bulk historical Spot candle ingestion uses official Binance public archives rather than REST pagination as the primary two-year source.
- [ ] Monthly and daily archive roles are defined for completed historical periods.
- [ ] Archive checksums are verified before ranges are treated as successfully ingested.
- [ ] Archive timestamp units, including 2025+ Spot archive semantics, are normalized deterministically.
- [ ] Historical archive import is durable, resumable, and idempotent.
- [ ] Completed ranges are skipped on subsequent maintenance/startup runs.
- [ ] REST is used only for bounded recent/missing/reconciliation work.
- [ ] Binance REST consumers share one conservative request-weight/rate-limit policy.
- [ ] HTTP 429 honors provider retry guidance and does not busy-retry.
- [ ] HTTP 418 stops unsafe retries and exposes an operational provider-ban state.
- [ ] Canonical retention covers exactly the approved 765-day product horizon unless future warm-up requirements increase it.
- [ ] Retention cleanup cannot delete data required by the supported backtest horizon.
- [ ] Full historical coverage runs in a dedicated background worker and does not block Web/API/core application readiness.
- [ ] Market-stream startup does not wait for the complete 765-day backfill.
- [ ] Features requiring history gate on actual canonical coverage; unrelated functions remain usable while backfill is incomplete.
- [ ] Backtests read canonical persisted candles only and never fetch Binance on demand or wait for background acquisition.
- [ ] Missing required canonical coverage fails safely and explicitly.
- [ ] An already-covered shorter backtest remains usable while deeper coverage is still backfilling.
- [ ] Dataset loading supports the bounded full-range 1h/4h candle counts plus warm-up without relying on a short-range magic cap.
- [ ] Existing historical reports remain immutable/readable.
- [ ] The web exposes 30D, 90D, 6M, 1Y, 2Y, and Custom period choices driven by server limits/coverage.
- [ ] The web shows safe actual coverage/backfill status and progressively unlocks longer presets without restarting the app.
- [ ] Local persistent history is not repeatedly downloaded after normal restarts.
- [ ] Deterministic E2E coverage proves application readiness independently from paused/incomplete background backfill and never contacts real Binance services.
- [ ] Current-state market-data, database, historical-analysis/backtesting, API, web, architecture, operations, observability, E2E, README, concerns, and continuity documentation remain synchronized during implementation.

## Implementation Issues

- #151 — Add resumable Binance bulk historical candle ingestion
- #152 — Add shared Binance REST rate-budget and safe candle reconciliation
- #153 — Maintain rolling two-year canonical candle coverage
- #159 — Run long-range candle backfill in background without blocking app readiness
- #154 — Expand historical-analysis range to the latest 730 days
- #155 — Add long-range historical-analysis date presets and coverage UX
- #156 — Cover two-year historical coverage and resumable market-data backfill

Implementation order:

```text
#151 → #152 → #153 → #159 → #154 → #155 → #156
```

Each issue requires an explicitly approved technical solution comment before implementation.

## Verification Boundary

Planning approval does not authorize database migrations/commands, provider downloads, real Binance requests, services, backfills, historical simulations, builds, tests, Playwright/E2E, browser interaction, package installation, linting, formatting checks, type checks, documentation generators, or other verification commands. Those remain subject to explicit maintainer direction.