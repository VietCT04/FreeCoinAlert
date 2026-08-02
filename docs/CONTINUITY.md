# Continuity

## Current Snapshot

- Account sessions, CSRF protection, and browser authentication are implemented; see [SECURITY.md](SECURITY.md).
- Private Telegram linking, test notifications, and durable outbox processing are implemented; see [TELEGRAM.md](TELEGRAM.md).
- The controlled Binance Spot catalogue and singleton market stream are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- Closed `1m` candles and derived `1h`/`4h` candles are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- One-time price-crossing alerts and their browser management surface are implemented; see [ALERTS.md](ALERTS.md) and [PRODUCT.md](PRODUCT.md).
- Fixed SMA 200 and RSI 14 preset subscriptions and global occurrences are implemented; see [STRATEGIES.md](STRATEGIES.md) and [ALERTS.md](ALERTS.md).
- The authenticated historical/live signal-feed API and SSE transport are implemented and Unverified; the authenticated browser preset catalog, subscription controls, history feed, visibility recovery, and optional browser sound are implemented by the current frontend surface. Backtesting remains Not supported.

## Active Work

- [#54](https://github.com/VietCT04/FreeCoinAlert/issues/54) - Add frontend preset controls and the live notification feed on the implemented authenticated feed API. The browser and audio paths remain Unverified.

## Current Blockers

- There is no current implementation blocker. A maintainer-requested browser/runtime verification pass remains outstanding.

See [CONCERNS.md](CONCERNS.md) for risks that do not block current work or safe operation.

## Verification Status

| Area | Availability | Verification | Note |
| --- | --- | --- | --- |
| Browser account and price alerts | Implemented | Unverified | No explicit browser or end-to-end pass was requested. |
| Telegram linking and delivery | Implemented | Unverified | Provider and worker paths were not exercised. |
| Market data and candles | Implemented | Unverified | Binance, maintenance, and reconciliation paths were not exercised. |
| Preset signal occurrences | Implemented | Unverified | Global occurrence evaluation and the authenticated feed boundary are available. |
| Signal history and live SSE | Implemented | Unverified | Durable history, cursor recovery, listener, and stream paths were not exercised. |
| Browser preset subscriptions and live feed | Implemented | Unverified | Browser, visibility, EventSource, and audio paths were not exercised. |
| Historical analysis | Not supported | Not applicable | No backtesting runtime exists. |

## Next Actions

1. Complete and merge #54 using its approved solution.
2. Request a dedicated verification pass when the maintainer is ready.

## Handoff Constraints

- Follow the documentation ownership and status vocabulary in [docs/README.md](README.md).
- Read the target issue, approved solution, and relevant authoritative documents before changing behavior.
- Keep GitHub issues and pull requests as implementation history; do not add completed-work diaries.
- Update every affected authoritative document and replace stale statements in the same change.
- Keep README files to setup and navigation, with links to detailed owners.
- Preserve authenticated ownership, exact-decimal market data, immutable event/version semantics, and separation of occurrence from delivery.
- Keep provider credentials, session/CSRF tokens, and sensitive identifiers out of logs and documentation examples.
- Do not run verification commands unless the maintainer explicitly requests a verification pass; see [AGENTS.md](../AGENTS.md).
