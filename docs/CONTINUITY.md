# Continuity

## Current Snapshot

- Account sessions, CSRF protection, and browser authentication are implemented; see [SECURITY.md](SECURITY.md).
- Private Telegram linking, test notifications, and durable outbox processing are implemented; see [TELEGRAM.md](TELEGRAM.md).
- The controlled Binance Spot catalogue and singleton market stream are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- Closed `1m` candles and derived `1h`/`4h` candles are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- One-time price-crossing alerts and their browser management surface are implemented; see [ALERTS.md](ALERTS.md) and [PRODUCT.md](PRODUCT.md).
- Fixed SMA 200 and RSI 14 preset subscriptions and global occurrences are implemented; see [STRATEGIES.md](STRATEGIES.md) and [ALERTS.md](ALERTS.md).
- Signal-feed delivery, frontend preset controls, browser sound, and backtesting are Planned or Not supported; see [PRODUCT.md](PRODUCT.md) and [BACKTESTING.md](BACKTESTING.md).

## Active Work

- [#53](https://github.com/VietCT04/FreeCoinAlert/issues/53) — Add an authenticated historical and live signal-event feed. It follows the merged preset-occurrence work; its approved solution is available and it has no current blocker.
- [#54](https://github.com/VietCT04/FreeCoinAlert/issues/54) — Add frontend preset controls and the live notification feed. It must follow #53; the feed API and stream are its current dependency.
- [#64](https://github.com/VietCT04/FreeCoinAlert/issues/64) — Enforce the current-state documentation workflow. It must follow the merge of this navigation/handoff change; its approved solution is available.

## Current Blockers

- #54 cannot begin until #53 is merged.
- #64 cannot begin until this Issue #63 pull request is merged.

See [CONCERNS.md](CONCERNS.md) for risks that do not block current work or safe operation.

## Verification Status

| Area | Availability | Verification | Note |
| --- | --- | --- | --- |
| Browser account and price alerts | Implemented | Unverified | No explicit browser or end-to-end pass was requested. |
| Telegram linking and delivery | Implemented | Unverified | Provider and worker paths were not exercised. |
| Market data and candles | Implemented | Unverified | Binance, maintenance, and reconciliation paths were not exercised. |
| Preset signal occurrences | Implemented | Unverified | Feed and user-facing signal delivery are Planned. |
| Historical analysis | Not supported | Not applicable | No backtesting runtime exists. |

## Next Actions

1. Merge this Issue #63 navigation and handoff change.
2. Implement #64 using its approved solution.
3. Implement #53, then #54, using their approved solutions.
4. Request a dedicated verification pass when the maintainer is ready.

## Handoff Constraints

- Follow the documentation ownership and status vocabulary in [docs/README.md](README.md).
- Read the target issue, approved solution, and relevant authoritative documents before changing behavior.
- Keep GitHub issues and pull requests as implementation history; do not add completed-work diaries.
- Update every affected authoritative document and replace stale statements in the same change.
- Keep README files to setup and navigation, with links to detailed owners.
- Preserve authenticated ownership, exact-decimal market data, immutable event/version semantics, and separation of occurrence from delivery.
- Keep provider credentials, session/CSRF tokens, and sensitive identifiers out of logs and documentation examples.
- Do not run verification commands unless the maintainer explicitly requests a verification pass; see [AGENTS.md](../AGENTS.md).
