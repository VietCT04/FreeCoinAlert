# Continuity

## Current Project State

FreeCoinAlert has an approved documentation baseline, a repository-level pnpm workspace foundation, runnable Next.js and FastAPI foundations, and a local Docker Compose stack with PostgreSQL pending this Issue #7 pull request. No application database integration, migrations, authentication, market-data processing, alerts, or automated tests exist yet.

US-0001 establishes the runnable project foundation. US-0002 is the approved next product capability: users can create an account, sign in, remain signed in, and sign out before Telegram connections and alerts are introduced.

The agreed product direction remains an alert-first web application where users connect Telegram, subscribe to available signal templates, or create validated custom alerts. Binance WebSocket data will drive real-time evaluation, closed one-minute candles will be stored as canonical history, and reconciliation will repair missing data. Future historical analysis will reuse the same strategy-core logic and internal candle database.

## Latest Completed Work

- **Date:** 2026-07-28
- **GitHub Issue:** #7 - Add local PostgreSQL and integrated development startup
- **Pull Request:** Pending - Add local PostgreSQL and integrated development startup
- **Summary:** Added the local Docker Compose stack, development Dockerfiles, persistent local PostgreSQL, integrated startup commands, safe local environment configuration, and operational documentation.
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

- **Completed implementation issues:** #4, #5, and #6
- **Active implementation:** Issue #7 in this pull request
- **Implementation status:** US-0001 becomes implementation-complete when Issue #7 is merged.
- **Verification status:** No test or dedicated full-foundation verification pass has been requested or run.

### US-0002: Create an Account and Sign In

- **User Story:** `docs/user-stories/US-0002-create-account-and-sign-in.md`
- **Documentation Pull Request:** #10 - merged
- **Status:** Approved documentation is merged.
- **Implementation Issues:** #11, #13, #14, and #15
- **Implementation dependency:** Authentication implementation must not begin until Issue #7 is merged.
- **Solution status:** No technical solution has been approved or posted for any US-0002 implementation issue yet.

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

Implementation order:

1. Merge Issues #6 and #7 to complete the required project foundation.
2. Implement Issue #11.
3. Implement Issue #13.
4. Implement Issue #14.
5. Implement Issue #15.

No implementation should begin until the relevant issue receives an explicitly approved solution comment.

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Important unresolved decisions include:

- Authentication and session design
- Product name and domain
- Initial Binance market and symbols
- Indicator library and numeric consistency
- Retention and hosting
- Telegram destination scope

## Market-Data State

- **Exchange integration:** Not implemented
- **Market:** Pending decision
- **Supported symbols:** None yet
- **Stored candle ranges:** None
- **Known data gaps:** Not applicable
- **Reconciliation status:** Not implemented

## Next Recommended Steps

1. Review and merge the Issue #7 pull request.
2. Request a dedicated full-foundation verification pass when the maintainer wants one.
3. Request a proposed technical solution for Issue #11 after Issue #7 is merged.
4. Continue US-0002 in issue order: #11, #13, #14, then #15.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`.
- Read `docs/README.md` and the relevant domain docs.
- Read US-0001, US-0002, and their linked implementation issues before changing project foundation or authentication behavior.
- Read US-0001 and Issues #4 through #7 before changing the project foundation.
- Treat PR #3 as documentation-only.
- Follow approved issue solutions without broadening them.
- Do not invent a technical solution for an implementation issue when no approved issue comment exists.
- Do not begin authentication implementation until Issue #7 is merged.
- Do not run tests or verification commands unless the maintainer explicitly requests them.
- Do not begin Telegram, Binance, alert, or backtesting work under US-0002.
- Avoid provider-specific infrastructure without an approved issue.
- Update this file after every meaningful change.
