# Continuity

## Current Project State

FreeCoinAlert has an approved documentation baseline but no application source code, database migrations, infrastructure definitions, or automated tests yet.

US-0001 defines the first stakeholder outcome: establish a consistent and runnable project foundation before authentication, Telegram integration, market-data ingestion, and alerts are implemented.

The agreed product direction remains an alert-first web application where users connect Telegram, subscribe to available signal templates, or create validated custom alerts. Binance WebSocket data will drive real-time evaluation, closed one-minute candles will be stored as canonical history, and reconciliation will repair missing data. Future historical analysis will reuse the same strategy-core logic and internal candle database.

## Latest Completed Work

- **Date:** 2026-07-28
- **GitHub Issue:** #1 — Establish project documentation baseline
- **Pull Request:** #2 — Establish project documentation baseline
- **Summary:** Merged the initial documentation source-of-truth structure, root README, and FreeCoinAlert-specific agent rules.
- **Files changed:** `README.md`, `AGENTS.md`, and the initial `docs/*.md` files.

## Active Work

- **User Story:** `docs/user-stories/US-0001-establish-project-foundation.md`
- **Current Pull Request:** #3 — Add US-0001 project foundation
- **Current goal:** Review and merge the approved user story and its stakeholder workflow documentation.
- **Implementation Issues:** #4, #5, #6, and #7
- **Current blocker:** No technical solution has been proposed or approved for any implementation issue yet.

## Important User Stories

### US-0001: Establish the Project Foundation

As a project maintainer, establish a consistent and runnable foundation so developers can implement future features without repeatedly deciding structure and setup.

Follow-up issues:

- #4 — Establish the monorepo workspace and developer conventions
- #5 — Bootstrap the frontend application
- #6 — Bootstrap the backend API and health endpoint
- #7 — Add local PostgreSQL and integrated development startup

No implementation should begin until the relevant issue receives an explicitly approved solution comment.

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Important unresolved decisions include:

- Exact monorepo and repository-level tooling
- Exact frontend stack and package choices
- Exact backend stack and package choices
- Local container and startup orchestration
- Product name and domain
- Initial Binance market and symbols
- Authentication approach
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

1. Review and merge PR #3.
2. Ask for a proposed solution to Issue #4 and approve or revise it.
3. Post the approved Issue #4 solution to its GitHub comment thread.
4. Implement Issue #4 through a separate pull request.
5. Repeat the solution-approval workflow for Issues #5 and #6.
6. Address Issue #7 after the required frontend, backend, and repository foundations are clear.
7. Propose US-0002 only after the project foundation direction is stable.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`.
- Read `docs/README.md` and the relevant domain docs.
- Read US-0001 and Issues #4 through #7 before changing the project foundation.
- Treat PR #3 as documentation-only.
- Do not invent a technical solution for an implementation issue when no approved issue comment exists.
- Do not begin authentication, Telegram, Binance, alert, or backtesting work under US-0001.
- Avoid provider-specific infrastructure without an approved issue.
- Update this file after every meaningful change.
