# Continuity

## Current Project State

FreeCoinAlert is in repository and product-documentation setup.

The repository currently contains no application source code, database migrations, infrastructure definitions, or automated tests.

The agreed direction is an alert-first web application where users connect Telegram, subscribe to available signal templates, or create validated custom alerts. Binance WebSocket data drives real-time evaluation, closed one-minute candles are stored as canonical history, and a reconciliation job repairs missing data. Future historical analysis will reuse the same strategy-core logic and internal candle database.

## Latest Completed Work

- **Date:** 2026-07-28
- **GitHub Issue:** #1 — Establish project documentation baseline
- **Summary:** Created the first project issue and prepared the documentation source-of-truth structure, root README, and FreeCoinAlert-specific agent rules.
- **Files changed:** `README.md`, `AGENTS.md`, and initial `docs/*.md` files in the linked pull request.

## Active Work

- **Current GitHub Issue:** #1
- **Current goal:** Review and merge the initial project documentation baseline.
- **Current blocker:** None. The implementation stack and first user story should be selected after documentation review.

## Important User Stories

No numbered user stories exist yet.

Recommended first product stories:

- User account registration and authentication
- Connect a private Telegram chat
- Create a price-above or price-below alert
- Receive and view a Telegram alert
- Pause, resume, and delete an alert

Create these as separate files under `docs/user-stories/` and split implementation into focused GitHub Issues.

## Known Concerns

See [`CONCERNS.md`](CONCERNS.md).

Important unresolved decisions include:

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

1. Review and merge the initial documentation pull request.
2. Create the first user story for account authentication or Telegram connection.
3. Create focused GitHub Issues from the approved user story.
4. Select the initial application stack and create the monorepo skeleton through an approved issue.
5. Add local Docker Compose only when the first executable components require it.

## Handoff Notes

Future agents must:

- Read root `AGENTS.md`.
- Read `docs/README.md` and the relevant domain docs.
- Check Issue #1 and its pull request before assuming the documentation baseline is merged.
- Avoid adding application code to the documentation issue.
- Avoid selecting provider-specific infrastructure without an approved issue.
- Update this file after every meaningful change.