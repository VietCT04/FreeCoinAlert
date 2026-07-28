# Continuity

## Current Project State

FreeCoinAlert has an approved documentation baseline, a repository-level pnpm workspace foundation, and a runnable Next.js frontend foundation. The backend API and local PostgreSQL/Compose foundation remain pending under US-0001. No authentication, Telegram integration, alert behavior, market-data ingestion, database schema, or automated tests exist yet.

US-0001 establishes the runnable project foundation. US-0002 is the approved next product capability: users can create an account, sign in, remain signed in, and sign out before Telegram connections and alerts are introduced.

The agreed product direction remains an alert-first web application where users connect Telegram, subscribe to available signal templates, or create validated custom alerts. Binance WebSocket data will drive real-time evaluation, closed one-minute candles will be stored as canonical history, and reconciliation will repair missing data. Future historical analysis will reuse the same strategy-core logic and internal candle database.

## Latest Completed Work

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

- **Completed implementation issues:** #4 and #5
- **Pending implementation issues:** #6 and #7
- **Current dependency:** Issue #6 must be implemented before Issue #7.

### US-0002: Create an Account and Sign In

- **User Story:** `docs/user-stories/US-0002-create-account-and-sign-in.md`
- **Status:** Approved by the maintainer; documentation PR is being prepared.
- **Implementation Issues:** To be created after the user-story PR is opened.
- **Implementation dependency:** Authentication implementation must not begin until the required backend and local database foundations from US-0001 are merged.

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

Follow-up issues will be linked after creation.

No implementation should begin until the relevant issue receives an explicitly approved solution comment.

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Important unresolved decisions include:

- Authentication and session design
- Local container and startup orchestration
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

1. Open and review the US-0002 documentation PR.
2. Create focused GitHub Issues from US-0002 and link them into the story.
3. Implement Issue #6 through its approved solution.
4. Implement Issue #7 after Issue #6 is merged.
5. Propose and approve solutions for US-0002 implementation issues only after their dependencies are available.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`.
- Read `docs/README.md` and the relevant domain docs.
- Read US-0001, US-0002, and their linked implementation issues before changing project foundation or authentication behavior.
- Do not invent a technical solution for an implementation issue when no approved issue comment exists.
- Do not begin authentication implementation until the backend and local database foundations required by US-0001 are merged.
- Do not run tests or verification commands unless the maintainer explicitly requests them.
- Do not begin Telegram, Binance, alert, or backtesting work under US-0002.
- Avoid provider-specific infrastructure without an approved issue.
- Update this file after every meaningful change.
