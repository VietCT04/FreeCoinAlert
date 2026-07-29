# Continuity

## Current Project State

FreeCoinAlert has an approved documentation baseline, a repository-level pnpm workspace foundation, runnable Next.js and FastAPI foundations, a local Docker Compose stack with PostgreSQL, and completed authentication persistence, registration/sign-in, and session-lifecycle API work.

US-0001 is implementation-complete. US-0002 is the active product implementation: authentication persistence, registration/sign-in, and session lifecycle are complete in code, while frontend authentication remains in Issue #15.

US-0003 is approved and documented in merged PR #18. Its implementation introduces one private Telegram destination per signed-in user through a short-lived, one-time deep-link flow. Telegram implementation must wait until US-0002 is implementation-complete.

The agreed product direction remains an alert-first web application where users connect Telegram, subscribe to available signal templates, or create validated custom alerts. Binance WebSocket data will drive real-time evaluation, closed one-minute candles will be stored as canonical history, and reconciliation will repair missing data. Future historical analysis will reuse the same strategy-core logic and internal candle database.

## Latest Completed Work

- **Date:** 2026-07-29
- **GitHub Issue:** #14 - Implement authenticated session, current-user, and logout API
- **Pull Request:** Pending creation from `agent/auth-session-lifecycle`
- **Summary:** Added reusable authenticated-principal and CSRF dependencies, current-user session restoration, idempotent current-session logout, safe authentication events, CORS support for the session lifecycle, and synchronized documentation.
- **Files changed:** `apps/api/src/freecoinalert_api/api/*`, `apps/api/src/freecoinalert_api/auth/principal.py`, `apps/api/src/freecoinalert_api/db/repositories/auth_sessions.py`, `apps/api/README.md`, `AGENTS.md`, and relevant API, security, architecture, observability, concern, and continuity documentation.

- **Date:** 2026-07-29
- **GitHub Issue:** #11 - Add user and authentication session persistence
- **Pull Request:** #17 - Add authentication persistence foundation
- **Summary:** Merged typed SQLAlchemy models, asynchronous session management, persistence repositories, Alembic configuration, the initial users and authentication-sessions migration, and local PostgreSQL integration.

- **Date:** 2026-07-28
- **GitHub Issue:** #7 - Add local PostgreSQL and integrated development startup
- **Pull Request:** #16 - Add local Compose development stack
- **Summary:** Merged the local Docker Compose stack, development Dockerfiles, persistent local PostgreSQL, integrated startup commands, safe local environment configuration, and operational documentation.
- **Files changed:** `compose.yaml`, `.dockerignore`, `.env.example`, `apps/*/Dockerfile.dev`, `package.json`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, and relevant component and operational documentation.

- **Date:** 2026-07-28
- **GitHub Issue:** #6 - Bootstrap the backend API and health endpoint
- **Pull Request:** #12 - Bootstrap the backend API and health endpoint
- **Summary:** Merged the FastAPI Python API foundation, uv lockfile, typed API process-health endpoint, backend command contracts, and safe API environment guidance.
- **Files changed:** `apps/api/*`, `package.json`, `AGENTS.md`, `README.md`, `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `docs/OBSERVABILITY.md`, `docs/CONCERNS.md`, and `docs/CONTINUITY.md`.

- **Date:** 2026-07-28
- **GitHub Issue:** #5 - Bootstrap the frontend application
- **Pull Request:** #9 - Bootstrap frontend application
- **Summary:** Merged the Next.js TypeScript App Router frontend, Tailwind CSS, frontend workspace commands, safe frontend environment guidance, and the frontend foundation page.
- **Files changed:** `apps/web/*`, `package.json`, `pnpm-lock.yaml`, `AGENTS.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `docs/CONCERNS.md`, and `docs/CONTINUITY.md`.

- **Date:** 2026-07-28
- **GitHub Issue:** #4 - Establish the monorepo workspace and developer conventions
- **Pull Request:** #8 - Establish monorepo workspace and developer conventions
- **Summary:** Merged the native pnpm workspace foundation, tooling conventions, contributor guidance, and repository boundary documentation.

- **Date:** 2026-07-28
- **GitHub Issue:** #1 - Establish project documentation baseline
- **Pull Request:** #2 - Establish project documentation baseline
- **Summary:** Merged the initial documentation source-of-truth structure, root README, and FreeCoinAlert-specific agent rules.

## Active Work

### US-0001: Establish the Project Foundation

- **Completed implementation issues:** #4, #5, #6, and #7
- **Implementation status:** Complete
- **Verification status:** No test or dedicated full-foundation verification pass has been requested or run.

### US-0002: Create an Account and Sign In

- **User Story:** `docs/user-stories/US-0002-create-account-and-sign-in.md`
- **Documentation Pull Request:** #10 - merged
- **Implementation Issues:** #11, #13, #14, and #15
- **Completed implementation:** Issues #11 and #13 are merged; Issue #14 is implemented on `agent/auth-session-lifecycle` and awaiting its pull request.
- **Remaining order:** #15 after Issue #14 merges.
- **Solution status:** Approved solutions are posted for all four issues.
- **Verification status:** No authentication verification pass has been requested or run.

### US-0003: Connect Telegram for Notifications

- **User Story:** `docs/user-stories/US-0003-connect-telegram-for-notifications.md`
- **Documentation Pull Request:** #18 - merged
- **Implementation Issues:** #19, #20, #21, #22, and #23
- **Implementation dependency:** US-0002 must be implementation-complete before Issue #19 begins.
- **Implementation order:** #19, #20, #21, #22, then #23
- **Solution status:** No technical solution has been approved or posted for any US-0003 issue yet.

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

No implementation should begin until the relevant issue receives an explicitly approved solution comment.

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Important unresolved decisions include:

- Product name and domain
- Initial Binance market and symbols
- Indicator library and numeric consistency
- Retention and hosting
- Telegram token lifetime and reconnection behavior
- Telegram update transport by environment
- Notification outbox claim, retry, and failure semantics
- Behavior of future active alerts after Telegram disconnects

## Market-Data State

- **Exchange integration:** Not implemented
- **Market:** Pending decision
- **Supported symbols:** None yet
- **Stored candle ranges:** None
- **Known data gaps:** Not applicable
- **Reconciliation status:** Not implemented

## Next Recommended Steps

1. Review and merge the Issue #13 registration and sign-in pull request, then implement US-0002 Issues #14 and #15 in order.
2. After US-0002 is complete, request proposed technical solutions for US-0003 beginning with Issue #19.
3. Request a dedicated verification pass only when the maintainer wants one.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`.
- Read `docs/README.md` and the relevant domain docs.
- Read the active user story and every linked implementation issue before changing behavior.
- Follow approved issue solutions without broadening them.
- Do not invent a technical solution for an implementation issue when no approved issue comment exists.
- Do not begin US-0003 implementation until US-0002 is complete.
- Derive ownership from the authenticated principal rather than client-provided user identifiers.
- Never ask users to type Telegram chat IDs manually.
- Never log Telegram bot tokens, raw linking tokens, raw session tokens, or full sensitive provider payloads.
- Do not run tests or verification commands unless the maintainer explicitly requests them.
- Avoid provider-specific production infrastructure without an approved issue.
- Update this file after every meaningful change.
