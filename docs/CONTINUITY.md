# Continuity

## Current Project State

## Latest completed work

### 2026-07-31 — Issue #52: preset signal evaluator and events

- Added global closed-candle SMA 200 and RSI 14 preset evaluation in the existing market-stream process, durable per-market/preset state, immutable deduplicated signal events, and separate invalidation records.
- Added exact equality-aware crossing semantics, safe suspension for unsafe candle data, explicit signal-backfill configuration and command boundary, and the `20260731_0011` migration.
- Browser feed delivery, user-specific event copies, Telegram notification jobs, and a second evaluator service remain out of scope.
- No provider, process, migration, backfill, test, build, lint, type-check, or verification command was run by maintainer direction.

### 2026-07-31 — Issue #51: shared SMA 200 and RSI 14 calculation core

- Added provider-neutral immutable candle, result, state, and shared-calculation-key contracts under `apps/api/src/freecoinalert_api/strategies/`.
- Implemented pure `sma_close_v1` and `rsi_wilder_close_v1` batch and incremental Decimal calculations, including typed invalid, gap, insufficient-history, and unsupported-version outcomes.
- Updated the Issue #50 seed hash to include the approved calculation version, and synchronized strategy, alert, market-data, architecture, concern, continuity, and API documentation.
- No live calculations, migrations, tests, builds, linting, formatting, type checks, or verification commands were run by maintainer direction.

### 2026-07-30 — Issue #50: versioned preset catalog and subscriptions

- Added immutable versioned signal-preset and user-subscription persistence with a migration that seeds eight approved version-1 presets.
- Added public preset listing and authenticated, CSRF-protected subscription enable/list/disable APIs with ownership controls, exact decimal thresholds, idempotent reactivation, advisory-lock limit enforcement, and bounded local rate limits.
- Updated related documentation. Indicator calculation, occurrences, feed delivery, Telegram behavior, and frontend work remain out of scope.

FreeCoinAlert has a pnpm monorepo, Next.js frontend, FastAPI backend, PostgreSQL persistence, local Docker Compose stack, authenticated user accounts, private Telegram linking, durable Telegram notification delivery, a controlled Binance Spot catalog, centralized live aggregate-trade ingestion, one-time price-crossing alerts, and an authenticated frontend alert flow.

US-0001 through US-0004 are implementation-complete in merged pull requests. No dedicated end-to-end verification pass has been requested or run for the complete product flow. Binance and Telegram integrations have been implemented but have not been contacted or exercised through a maintainer-requested verification pass.

US-0005 is approved. PR #47 documents preset indicator subscriptions, historical signal notifications, a live in-app feed, and an autoplay-safe notification sound. Issue #48 now has the approved candle-persistence implementation; Issues #49 through #54 remain pending their approved solutions and documented order.

## Latest Completed Work

- **Date:** 2026-07-30
- **GitHub Issue:** #48 - Add canonical candle and timeframe persistence
- **Pull Request:** Current draft
- **Summary:** Added the SQLAlchemy/Alembic `market_candles` persistence boundary for canonical closed `1m` candles and `1h`/`4h` derived windows, exact decimal constraints, current/revision state, bounded gap and range repository operations, and 180-day retention configuration. It does not contact Binance, schedule aggregation, bootstrap history, calculate indicators, evaluate presets, or expose APIs.
- **Verification status:** No migration, database command, provider request, application or Compose startup, test, build, lint, format, type check, or other verification command was run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #33 - Add frontend one-time price alert flow
- **Pull Request:** #46 - Add frontend one-time price alert flow
- **Summary:** Merged the authenticated catalog-backed one-time price-alert form, owned alert list, safe lifecycle and Telegram-delivery summaries, deletion flow, cursor pagination, and bounded visibility-aware refresh behavior.
- **Verification status:** No browser interaction, API, Binance, or Telegram requests, application startup, tests, builds, linting, formatting checks, type checks, or other verification commands were run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #32 - Evaluate price crossings and queue Telegram alerts
- **Pull Request:** #45 - Evaluate price crossings and queue Telegram alerts
- **Summary:** Merged exact crossing semantics, durable active-alert evaluation, atomic alert-event and notification-outbox creation, price-alert Telegram messages, and separate alert lifecycle and delivery state.
- **Verification status:** Binance and Telegram were not contacted. No workers, migrations, database commands, startup, tests, builds, linting, formatting checks, type checks, or other verification commands were run.

- **Date:** 2026-07-30
- **GitHub Issue:** #31 - Add centralized Binance live price stream
- **Pull Request:** #43 - Add centralized Binance live price stream
- **Summary:** Merged the singleton centralized Binance Spot aggregate-trade stream, exact-decimal normalized events, bounded ordered pipeline, durable latest-symbol state, freshness handling, reconnect behavior, and optional market Compose profile.
- **Verification status:** Binance was not contacted and the stream was not started.

## Active User Stories

### US-0001: Establish the Project Foundation

- **Implementation Issues:** #4, #5, #6, and #7
- **Implementation status:** Complete
- **Verification status:** No dedicated full-foundation verification pass has been requested or run.

### US-0002: Create an Account and Sign In

- **User Story:** `docs/user-stories/US-0002-create-account-and-sign-in.md`
- **Documentation Pull Request:** #10 - merged
- **Implementation Issues:** #11, #13, #14, and #15
- **Implementation status:** Complete
- **Verification status:** No authentication verification pass has been requested or run.

### US-0003: Connect Telegram for Notifications

- **User Story:** `docs/user-stories/US-0003-connect-telegram-for-notifications.md`
- **Documentation Pull Request:** #18 - merged
- **Implementation Issues:** #19, #20, #21, #22, and #23
- **Implementation status:** Complete
- **Verification status:** No configured-bot Telegram verification pass has been requested or run.

### US-0004: Create a One-Time Cryptocurrency Price Alert

- **User Story:** `docs/user-stories/US-0004-create-one-time-price-alert.md`
- **Documentation Pull Request:** #27 - merged
- **Implementation Issues:** #28, #29, #30, #31, #32, and #33
- **Implementation status:** Complete; PRs #39, #41, #42, #43, #45, and #46 are merged.
- **Verification status:** No complete catalog, market-stream, trigger, Telegram-delivery, or browser verification pass has been requested or run.

### US-0005: Subscribe to Preset Indicator Signals

- **User Story:** `docs/user-stories/US-0005-subscribe-to-preset-indicator-signals.md`
- **Documentation Pull Request:** #47 - merged
- **Implementation Issues:** #48, #49, #50, #51, #52, #53, and #54
- **Implementation order:** #48, #49, #50, #51, #52, #53, then #54
- **Solution status:** Issues #48 and #49 have approved solutions; #48 is merged and #49 is implementation-complete in the current draft pull request.
- **Implementation status:** Candle persistence and centralized closed-candle ingestion, bounded bootstrap/reconciliation paths, aggregation, and operational state are implemented; Issues #50 through #54 are not started.

Issue map:

- #48 - Add canonical candle and timeframe persistence
- #49 - Add Binance candle ingestion, bootstrap, and reconciliation
- #50 - Add versioned preset catalog and user subscriptions
- #51 - Add shared SMA 200 and RSI 14 calculation core
- #52 - Evaluate preset strategies and persist signal events
- #53 - Add historical feed and live in-app event stream
- #54 - Add frontend preset subscriptions and live notification feed

No implementation should begin until the relevant issue receives an explicitly approved technical solution comment.

## Product Direction

The current MVP supports user authentication, Telegram connection, and user-created one-time Binance Spot price alerts.

US-0005 adds maintained signal presets rather than user-defined formulas. Users will enable fixed preset and symbol combinations, review past signal occurrences, and receive live in-app feed updates. A new event received while the page is visible may play a short built-in sound after browser user activation. The user can mute the sound, and only the safe sound preference may be persisted in browser storage.

Signal occurrence, in-app feed visibility, notification sound playback, and Telegram delivery are separate states.

## Market-Data State

- **Exchange:** Binance Spot
- **Supported symbols:** BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT
- **Live source:** Centralized aggregate-trade stream implemented but not started or verified
- **Price-alert evaluation:** Implemented but not exercised through a dedicated verification pass
- **Canonical candle storage:** Implemented as database and repository boundaries; not populated or verified
- **Closed-candle ingestion:** Implemented in the singleton market stream; not started or verified
- **Historical candle bootstrap:** Explicit bounded command implemented; not executed or verified
- **Timeframe aggregation:** `1h` and `4h` aggregation paths implemented; not started or verified
- **Gap reconciliation:** Explicit and recent bounded paths implemented; not executed or verified
- **Indicator calculations:** Shared SMA 200 and Wilder RSI 14 core implemented; not exercised through a verification pass
- **Preset signal events:** Not implemented
- **Historical and live in-app feed:** Not implemented

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Important unresolved US-0005 decisions include:

- Binance kline ingestion and historical bootstrap boundaries
- Reconciliation cadence and correction semantics
- Initial preset catalog, versions, symbols, and timeframes
- SMA 200 and RSI 14 calculation semantics and numeric precision
- Historical/live event boundary and deduplication
- Signal-event ownership and retention
- Live browser transport, reconnect, replay, and production proxy behavior
- Browser autoplay activation, sound generation, mute storage, and replay prevention

## Next Recommended Steps

1. Continue Issue #52 for preset evaluation and immutable signal occurrences after approval.
2. Request a dedicated verification pass only when the maintainer wants it.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`, `docs/README.md`, the active user story, and all relevant domain documentation.
- Read the target issue and its approved solution comment before implementation.
- Do not invent or broaden a technical solution that has not been explicitly approved.
- Preserve the existing supported-market catalog and authenticated-principal ownership boundaries.
- Use exact decimal arithmetic for persisted market prices and candle values unless an approved indicator solution defines a safe bounded calculation representation.
- Persist only confirmed closed one-minute candles as canonical candle history.
- Do not evaluate indicator presets from incomplete, stale, invalid, or insufficient candle data.
- Keep preset definitions versioned and historical signal events immutable.
- Use the same approved strategy logic for historical and live calculations.
- Deduplicate historical feed and live events by stable event identity.
- Do not play notification sounds for historical replay, hidden-page events, or events received before browser user activation.
- Persist only the safe sound preference in browser storage.
- Keep signal occurrence, in-app delivery, sound playback, and Telegram delivery separate.
- Never log provider secrets, Telegram secrets, session or CSRF tokens, full provider payloads, or sensitive identifiers.
- Do not run tests or verification commands unless the maintainer explicitly requests them.
- Update this file after every meaningful change.
