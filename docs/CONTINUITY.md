# Continuity

## Current Project State

FreeCoinAlert has an approved documentation baseline, a repository-level pnpm workspace, runnable Next.js and FastAPI foundations, a local Docker Compose stack with PostgreSQL, and complete authentication persistence, API, and frontend flows.

US-0001 and US-0002 are implementation-complete. No dedicated foundation or authentication verification pass has been requested or run.

US-0003 is approved and documented in merged PR #18. Issues #19 through #23 are merged. Telegram
verification remains deliberately pending a maintainer-requested pass.

US-0004 is approved and documented in merged PR #27. Issues #28 through #30 are merged. Issue #31 has
an approved centralized live-price-stream implementation on `agent/binance-live-price-stream`; alert evaluation
and notification creation remain later work.

The broader direction remains an alert-first application. Binance public market data will drive centralized real-time evaluation. Closed one-minute candles, larger timeframe aggregation, reconciliation, indicator alerts, and historical analysis remain later capabilities.

## Latest Work

- **Date:** 2026-07-30
- **GitHub Issue:** #31 - Add centralized Binance live price stream
- **Pull Request:** Pending creation
- **Summary:** Added a separately runnable, singleton-locked Binance Spot aggregate-trade process for the
  controlled ready catalog, immutable exact-decimal internal events, per-connection ordering, bounded internal
  pipeline, durable throttled latest-symbol state, bounded reconnect behavior, optional Compose profile, and
  supporting operational documentation. It does not evaluate alerts, create alert events or notification jobs,
  expose current prices, or persist trade history.
- **Verification status:** Binance was not contacted and the stream was not started. No migrations, database
  commands, API or Compose startup, tests, builds, linting, formatting checks, type checks, or other verification
  commands were run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #30 - Implement authenticated one-time price alert API
- **Pull Request:** #42 - Implement authenticated price alert API (merged)
- **Summary:** Added session-authenticated alert create/list/read/soft-delete routes, exact-decimal validation,
  catalog and connected-Telegram gates, idempotency, opaque cursor pagination, transactionally enforced active
  limit, bounded local rate limiting, safe responses/errors, and supporting documentation. No live Binance
  lookup or stream, evaluator, alert-event/outbox write, Telegram message, frontend, migration, or test files.
- **Verification status:** No migration, database command, API startup, HTTP request, test, Docker/Compose command,
  build, lint, format, type check, or other verification command was run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #29 - Add one-time price alert persistence
- **Pull Request:** #41 - Add one-time price alert persistence (merged)
- **Summary:** Added PostgreSQL one-time price-alert and immutable alert-event schema, exact-decimal
  constraints, snapshot and lifecycle invariants, locked repository operations, and the Alembic migration.
  No API route, Binance stream, evaluator, outbox write, Telegram behavior, or frontend was added.
- **Verification status:** No migration, database command, test, application startup, HTTP request,
  build, lint, format, type check, or other verification command was run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #28 - Add supported Binance Spot market catalog
- **Pull Request:** #39 - Add supported Binance Spot market catalog (merged)
- **Summary:** Added the fixed five-symbol Binance Spot USDT catalog, seeded `supported_markets` migration,
  exact-decimal public metadata sync boundary, public safe `/markets` API, and explicit `market:sync`
  command without WebSocket ingestion, scheduling, or alert creation.
- **Verification status:** Binance was not contacted. No sync, migrations, database commands, API startup,
  HTTP requests, Docker commands, tests, builds, linting, formatting, type checks, or verification commands
  were run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #23 - Add frontend Telegram connection and test-notification flow
- **Pull Request:** #38 - Add frontend Telegram connection flow (draft)
- **Summary:** Added the authenticated root-route Telegram panel, credentialed typed browser API client,
  in-memory deep-link and idempotency handling, bounded visibility-aware connection and delivery polling,
  safe error feedback, and an inline disconnect confirmation without new frontend dependencies.
- **Verification status:** No browser interaction, API requests, Telegram links or contact, tests, builds,
  linting, type checks, or other verification commands were run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #22 - Add Telegram test-notification outbox and delivery worker
- **Pull Request:** #37 - Implement Telegram test notification outbox
- **Summary:** Added the PostgreSQL test-notification outbox, safe idempotent queue and status API,
  bounded local request limiting, separately runnable lock-safe worker, connection degradation,
  Compose profile integration, and operational documentation.
- **Verification status:** The worker was not run, Telegram was not contacted, and no tests,
  migrations, builds, or verification commands were run by maintainer direction.

- **Date:** 2026-07-30
- **GitHub Issue:** #21 - Implement Telegram bot update processing and account linking
- **Pull Request:** Pending creation
- **Summary:** Added the local sequential long-polling processor, typed Telegram client boundary,
  private `/start` parsing, atomic token and connection linking with `update_id` idempotency,
  one post-commit confirmation attempt, bounded processed-update cleanup, optional Compose profile,
  and safe Bot API configuration. Production webhooks, notification delivery, frontend UI, and tests
  remain out of scope.

## Latest Completed Work

- **Date:** 2026-07-30
- **GitHub Issue:** #20 - Implement authenticated Telegram connection API
- **Pull Request:** #35 - Implement Telegram connection API
- **Summary:** Merged session-authenticated, CSRF-protected link-token and disconnect endpoints,
  safe connection-state retrieval, one-time 32-byte token generation and SHA-256 persistence,
  transactional replacement and disconnect revocation, Telegram configuration, and bounded
  process-local rate limits.

- **Date:** 2026-07-29
- **GitHub Issue:** #15 - Add frontend registration, sign-in, and sign-out flow
- **Pull Request:** #26 - Implement frontend authentication flow
- **Summary:** Merged the in-memory authentication provider, credentialed browser API client, accessible registration and sign-in forms, session restoration, and current-session sign-out without persistent browser storage of authentication secrets.

- **Date:** 2026-07-29
- **GitHub Issue:** #14 - Implement authenticated session, current-user, and logout API
- **Pull Request:** #25 - Implement authenticated session lifecycle API
- **Summary:** Merged reusable authenticated-principal and CSRF dependencies, current-user restoration, idempotent logout, safe authentication events, and credentialed CORS support.

- **Date:** 2026-07-29
- **GitHub Issue:** #13 - Implement account registration and sign-in API
- **Pull Request:** #24 - Implement account registration and sign-in API
- **Summary:** Merged registration and login, Argon2id password hashing, opaque server-side sessions, credentialed cookies, safe authentication errors, origin validation, and bounded application-local rate limiting.

- **Date:** 2026-07-29
- **GitHub Issue:** #11 - Add user and authentication session persistence
- **Pull Request:** #17 - Add authentication persistence foundation
- **Summary:** Merged typed SQLAlchemy models, asynchronous session management, persistence repositories, Alembic configuration, the initial users and authentication-sessions migration, and local PostgreSQL integration.

- **Date:** 2026-07-29
- **User Story:** US-0003 - Connect Telegram for Notifications
- **Pull Request:** #18 - Add US-0003 Telegram connection
- **Summary:** Merged the approved Telegram connection story and linked implementation Issues #19 through #23.

- **Date:** 2026-07-28
- **GitHub Issue:** #7 - Add local PostgreSQL and integrated development startup
- **Pull Request:** #16 - Add local Compose development stack
- **Summary:** Merged the local Docker Compose stack, development Dockerfiles, persistent PostgreSQL, integrated startup commands, safe local environment configuration, and operational documentation.

- **Date:** 2026-07-28
- **GitHub Issue:** #6 - Bootstrap the backend API and health endpoint
- **Pull Request:** #12 - Bootstrap the backend API and health endpoint
- **Summary:** Merged the FastAPI Python API foundation, uv lockfile, typed process-health endpoint, backend command contracts, and safe API environment guidance.

- **Date:** 2026-07-28
- **GitHub Issue:** #5 - Bootstrap the frontend application
- **Pull Request:** #9 - Bootstrap frontend application
- **Summary:** Merged the Next.js TypeScript App Router frontend, Tailwind CSS, frontend workspace commands, safe frontend environment guidance, and frontend foundation page.

- **Date:** 2026-07-28
- **GitHub Issue:** #4 - Establish the monorepo workspace and developer conventions
- **Pull Request:** #8 - Establish monorepo workspace and developer conventions
- **Summary:** Merged the native pnpm workspace foundation, tooling conventions, contributor guidance, and repository boundary documentation.

- **Date:** 2026-07-28
- **GitHub Issue:** #1 - Establish project documentation baseline
- **Pull Request:** #2 - Establish project documentation baseline
- **Summary:** Merged the initial source-of-truth documentation structure, root README, and FreeCoinAlert-specific agent rules.

## Active Work

### US-0001: Establish the Project Foundation

- **Implementation Issues:** #4, #5, #6, and #7
- **Implementation status:** Complete
- **Verification status:** No dedicated full-foundation verification pass has been requested or run.

### US-0002: Create an Account and Sign In

- **User Story:** `docs/user-stories/US-0002-create-account-and-sign-in.md`
- **Documentation Pull Request:** #10 - merged
- **Implementation Issues:** #11, #13, #14, and #15
- **Implementation status:** Complete; PRs #17, #24, #25, and #26 are merged.
- **Solution status:** Approved solutions are posted for all four issues.
- **Verification status:** No authentication verification pass has been requested or run.

### US-0003: Connect Telegram for Notifications

- **User Story:** `docs/user-stories/US-0003-connect-telegram-for-notifications.md`
- **Documentation Pull Request:** #18 - merged
- **Implementation Issues:** #19, #20, #21, #22, and #23
- **Implementation order:** #19, #20, #21, #22, then #23
- **Solution status:** Approved solutions are posted for all five issues.
- **Implementation status:** Issues #19 through #23 are merged.
- **Verification status:** No Telegram verification pass has been requested or run.

### US-0004: Create a One-Time Cryptocurrency Price Alert

- **User Story:** `docs/user-stories/US-0004-create-one-time-price-alert.md`
- **Documentation Pull Request:** #27 - merged
- **Implementation Issues:** #28, #29, #30, #31, #32, and #33
- **Implementation dependency:** Issues #28 through #30 are merged; Issue #31 is implemented in the current draft pull request.
- **Implementation order:** #28, #29, #30, #31, #32, then #33
- **Solution status:** Issues #28 through #31 have approved solutions; later issues await solutions.
- **Verification status:** No catalog verification pass has been requested or run.

## Important User Stories

### US-0001: Establish the Project Foundation

As a project maintainer, establish a consistent and runnable foundation so developers can implement future features without repeatedly deciding structure and setup.

Follow-up issues:

- #4 - Establish the monorepo workspace and developer conventions
- #5 - Bootstrap the frontend application
- #6 - Bootstrap the backend API and health endpoint
- #7 - Add local PostgreSQL and integrated development startup

### US-0002: Create an Account and Sign In

As a user, create an account and sign in so alerts and the Telegram connection are saved securely and belong only to that user.

Follow-up issues:

- #11 - Add user and authentication session persistence
- #13 - Implement account registration and sign-in API
- #14 - Implement authenticated session, current-user, and logout API
- #15 - Add frontend registration, sign-in, and sign-out flow

### US-0003: Connect Telegram for Notifications

As a signed-in user, connect a private Telegram chat so FreeCoinAlert can send cryptocurrency alerts directly to that user.

Follow-up issues:

- #19 - Add Telegram connection and linking-token persistence
- #20 - Implement authenticated Telegram connection API
- #21 - Implement Telegram bot update processing and account linking
- #22 - Add Telegram test-notification outbox and delivery worker
- #23 - Add frontend Telegram connection and test-notification flow

### US-0004: Create a One-Time Cryptocurrency Price Alert

As a signed-in user with Telegram connected, create a price alert for a supported cryptocurrency so Telegram receives one notification when the price crosses the selected target.

Follow-up issues:

- #28 - Add supported Binance Spot market catalog
- #29 - Add one-time price alert persistence
- #30 - Implement authenticated one-time price alert API
- #31 - Add centralized Binance live price stream
- #32 - Evaluate price crossings and queue Telegram alerts
- #33 - Add frontend one-time price alert flow

No implementation should begin until the relevant issue receives an explicitly approved solution comment.

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Important unresolved decisions include:

- Product name and domain
- Telegram update transport for production
- Notification outbox claim, retry, and failure semantics
- Catalog refresh scheduling and production provider-rate-limit behavior
- Exact live-price source and price semantics
- Decimal precision and target-price validation
- Price-crossing initialization, equality, duplicate, stale, and out-of-order behavior
- Market-data freshness threshold for suspending evaluation
- Maximum active price alerts per user
- Alert retention and deletion behavior
- Hosting and production process management

## Market-Data State

- **Exchange integration:** Not implemented
- **Initial market:** Binance Spot, USDT quote asset
- **Supported symbols:** BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT (metadata pending explicit sync)
- **Live price stream:** Issue #31 implements an optional centralized Binance Spot aggregate-trade stream with durable latest-symbol state; it has not been started or verified.
- **Stored candle ranges:** None
- **Known data gaps:** Not applicable
- **Reconciliation status:** Not implemented

## Next Recommended Steps

1. Review and merge the Issue #31 centralized live-price stream pull request.
2. Implement Issue #32 only after its approved solution is available.
3. Request dedicated verification passes only when the maintainer wants them.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`.
- Read `docs/README.md` and the relevant domain documents.
- Read the active user story and every linked implementation issue before changing behavior.
- Follow approved issue solutions without broadening them.
- Do not invent a technical solution for an implementation issue when no approved issue comment exists.
- Do not merge Issue #28 before its stacked final Telegram-contract dependency, PR #38.
- Derive all ownership from the authenticated principal rather than client-provided user identifiers.
- Never ask users to type Telegram chat IDs manually.
- Accept only approved exchanges, markets, and symbols.
- Use exact decimal arithmetic for prices and targets; do not use binary floating-point values for persisted financial data.
- Keep alert triggering separate from notification delivery state.
- Create an alert event and notification-outbox job atomically when an alert triggers.
- Never log Telegram bot tokens, raw linking tokens, raw session tokens, provider secrets, or full sensitive provider payloads.
- Do not run tests or verification commands unless the maintainer explicitly requests them.
- Avoid provider-specific production infrastructure without an approved issue.
- Update this file after every meaningful change.
