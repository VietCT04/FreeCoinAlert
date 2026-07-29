# Continuity

## Current Project State

FreeCoinAlert has an approved documentation baseline, a repository-level pnpm workspace, runnable Next.js and FastAPI foundations, a local Docker Compose stack with PostgreSQL, and complete authentication persistence, API, and frontend flows.

US-0001 and US-0002 are implementation-complete. No dedicated foundation or authentication verification pass has been requested or run.

US-0003 is approved and documented in merged PR #18. Issue #19 persistence is merged, and
Issue #20 now has a draft authenticated connection API implementation. Telegram transport,
update processing, confirmation, delivery, and frontend work remain deliberately out of scope.
Approved technical solutions are posted for Issues #21 through #23.

US-0004 is approved and documented in draft PR #27. It introduces the first end-to-end product alert: a one-time supported cryptocurrency price crossing that creates an immutable alert event and queues a Telegram notification. US-0004 implementation must wait until US-0003 is implementation-complete.

The broader direction remains an alert-first application. Binance public market data will drive centralized real-time evaluation. Closed one-minute candles, larger timeframe aggregation, reconciliation, indicator alerts, and historical analysis remain later capabilities.

## Latest Work

- **Date:** 2026-07-30
- **GitHub Issue:** #20 - Implement authenticated Telegram connection API
- **Pull Request:** #35 - Implement Telegram connection API (draft)
- **Summary:** Added session-authenticated, CSRF-protected link-token and disconnect endpoints,
  safe connection-state retrieval, one-time 32-byte token generation and SHA-256 persistence,
  transactional replacement and disconnect revocation, Telegram configuration, and bounded
  process-local rate limits. Telegram Bot API calls, update processing, confirmations, delivery,
  frontend UI, and tests remain out of scope.

## Latest Completed Work

- **Date:** 2026-07-30
- **GitHub Issue:** #19 - Add Telegram connection and linking-token persistence
- **Pull Request:** #34 - Add Telegram connection persistence
- **Summary:** Merged typed SQLAlchemy persistence models, asynchronous repositories, and an
  Alembic migration for one private Telegram connection per user, SHA-256 token-hash lifecycle
  state, and idempotent processed-update records.

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
- **Implementation status:** Issue #19 is merged. Issue #20 has a draft implementation;
  #21 through #23 have not started.
- **Verification status:** No Telegram verification pass has been requested or run.

### US-0004: Create a One-Time Cryptocurrency Price Alert

- **User Story:** `docs/user-stories/US-0004-create-one-time-price-alert.md`
- **Documentation Pull Request:** #27 - draft
- **Implementation Issues:** #28, #29, #30, #31, #32, and #33
- **Implementation dependency:** US-0003 must be implementation-complete before Issue #28 begins.
- **Implementation order:** #28, #29, #30, #31, #32, then #33
- **Solution status:** No technical solution has been approved or posted for any US-0004 issue yet.
- **Verification status:** Not applicable until implementation exists.

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
- Initial Binance Spot symbols and catalog-refresh policy
- Exact live-price source and price semantics
- Decimal precision and target-price validation
- Price-crossing initialization, equality, duplicate, stale, and out-of-order behavior
- Market-data freshness threshold for suspending evaluation
- Maximum active price alerts per user
- Alert retention and deletion behavior
- Hosting and production process management

## Market-Data State

- **Exchange integration:** Not implemented
- **Initial market:** To be approved in Issue #28
- **Supported symbols:** None yet
- **Live price stream:** Not implemented
- **Stored candle ranges:** None
- **Known data gaps:** Not applicable
- **Reconciliation status:** Not implemented

## Next Recommended Steps

1. Review and merge documentation PR #27.
2. Review and merge the Issue #20 connection API pull request, then implement US-0003 in
   order: #21, #22, then #23.
3. After US-0003 is complete, request proposed technical solutions for US-0004 beginning with Issue #28.
4. Request dedicated verification passes only when the maintainer wants them.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`.
- Read `docs/README.md` and the relevant domain documents.
- Read the active user story and every linked implementation issue before changing behavior.
- Follow approved issue solutions without broadening them.
- Do not invent a technical solution for an implementation issue when no approved issue comment exists.
- Do not begin US-0004 implementation until US-0003 is implementation-complete.
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
