# Continuity

## Current Project State

FreeCoinAlert currently includes:

- A pnpm monorepo with a Next.js frontend, FastAPI backend, PostgreSQL, and Docker Compose development stack.
- Account registration, authenticated sessions, CSRF protection, and sign-out.
- Private Telegram account linking and durable Telegram notification delivery.
- A controlled Binance Spot catalog for BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, and XRPUSDT.
- A centralized singleton market process for aggregate trades and confirmed closed one-minute candles.
- Exact-decimal canonical `1m` candle persistence and UTC-aligned `1h` and `4h` aggregation.
- Bounded historical candle bootstrap and reconciliation command paths.
- User-created one-time price-crossing alerts and the authenticated browser alert flow.
- Eight immutable versioned SMA 200 and RSI 14 presets with authenticated user subscriptions.
- Shared provider-neutral SMA 200 and Wilder RSI 14 calculation logic.
- Global closed-candle preset evaluation with durable state, immutable signal events, and correction invalidations.

US-0001 through US-0004 are implementation-complete.

US-0005 is implemented through Issue #52. The historical/live signal feed and frontend preset feed with notification sound remain open in Issues #53 and #54.

The repository has not received a maintainer-requested end-to-end verification pass. Binance and Telegram integrations, migrations, workers, browser flows, candle bootstrap, reconciliation, and signal backfill must not be described as verified merely because their implementation is merged.

## Active Work

### US-0005: Subscribe to Preset Indicator Signals

- **Completed:** Issues #48 through #52
- **Open:**
  - #53 — Historical feed and live in-app event stream
  - #54 — Frontend preset subscriptions, live feed, highlighting, and notification sound
- **Implementation order:** #53, then #54
- **Solution status:** Approved technical solutions are posted for both open issues.

### US-0006: Maintain Current-State Product and Technical Documentation

- **User story:** `docs/user-stories/US-0006-maintain-current-state-documentation.md`
- **Documentation PR:** #60
- **Implementation issues:**
  - #61 — Core product and system contracts
  - #62 — Runtime and domain behavior
  - #63 — Documentation ownership, navigation, and concise handoff
  - #64 — Contributor workflow enforcement
- **Implementation order:** #61, #62, #63, then #64
- **Status:** Approved; implementation solutions have not yet been proposed or posted.

## Current Blockers and Concerns

- Domain documents may contain stale pending statements, issue-specific completion notes, duplicated rules, or contradictions.
- `AGENTS.md` currently contains duplicated documentation-staleness rules and requires more detailed historical content in this file than the new current-state model permits.
- Historical/live signal-feed transport and the frontend notification-sound experience are not implemented yet.
- No complete runtime or provider verification pass has been requested.

See [`CONCERNS.md`](CONCERNS.md) for unresolved technical and product risks.

## Next Recommended Steps

1. Merge PR #60.
2. Propose and approve the technical documentation plans for Issues #61 through #64.
3. Complete the current-state documentation audit in order: #61, #62, #63, then #64.
4. Implement Issue #53 using its approved solution.
5. Implement Issue #54 after #53 is merged.
6. Run dedicated verification only when explicitly requested by the maintainer.

## Handoff Rules

Future contributors must:

- Treat domain documents as descriptions of current implemented behavior, not issue history.
- Read the authoritative domain documents, the target issue, and its approved solution before changing code.
- Update every affected authoritative document in the same change as behavior modifications.
- Replace stale or superseded statements instead of appending issue-specific completion notes.
- Keep implemented, planned, unresolved, and unverified behavior clearly separated.
- Keep this file concise: current state, active work, blockers, concerns, and next steps only.
- Preserve exact-decimal market-data rules, authenticated ownership boundaries, immutable/versioned strategies and events, and separation between signal occurrence and delivery.
- Never log provider secrets, Telegram secrets, session or CSRF tokens, or sensitive identifiers.
- Do not run tests or verification commands unless the maintainer explicitly requests them.
