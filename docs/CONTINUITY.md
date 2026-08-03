# Continuity

## Current Snapshot

- Account sessions, CSRF protection, and browser authentication are implemented; see [SECURITY.md](SECURITY.md).
- Private Telegram linking, test notifications, and durable outbox processing are implemented; see [TELEGRAM.md](TELEGRAM.md).
- The controlled Binance Spot catalogue and singleton market stream are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- Closed `1m` candles and derived `1h`/`4h` candles are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- One-time price-crossing alerts and their browser management surface are implemented; see [ALERTS.md](ALERTS.md) and [PRODUCT.md](PRODUCT.md).
- Fixed SMA 200 and RSI 14 preset subscriptions and global occurrences are implemented; see [STRATEGIES.md](STRATEGIES.md) and [ALERTS.md](ALERTS.md).
- Per-subscription Telegram-delivery preference storage, immutable occurrence-time subscription state history, owner-scoped readiness responses, and the CSRF-protected preference API are implemented; the preference is disabled by default. Active preset cards provide server-confirmed enable/disable controls with inline enable confirmation, and Telegram connection changes refresh readiness without changing subscription state. New live occurrences also have durable dispatch rows, occurrence-time eligibility, bounded cursor fan-out, idempotent immutable-snapshot outbox jobs, database-only recovery, and notification-worker delivery with strict payload and send-time safety checks. See [API.md](API.md), [DATABASE.md](DATABASE.md), [ALERTS.md](ALERTS.md), and [TELEGRAM.md](TELEGRAM.md).
- The authenticated historical/live signal-feed API and SSE transport are implemented and Unverified; the authenticated browser preset catalog, subscription controls, Telegram-delivery controls, history feed, visibility recovery, and optional browser sound are implemented by the current frontend surface.
- Canonical historical-analysis dataset preparation, immutable candle snapshots, and the pure deterministic fixed-preset simulation engine are Implemented and Unverified; no worker invokes either boundary, and report persistence, cleanup, and browser analysis remain Planned or Not supported. See [BACKTESTING.md](BACKTESTING.md), [DATABASE.md](DATABASE.md), and [MARKET_DATA.md](MARKET_DATA.md).

## Active Work

- Provider-worker delivery is implemented but does not expose per-occurrence delivery history.

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
| Browser preset subscriptions, Telegram controls, and live feed | Implemented | Unverified | Browser, Telegram-control, visibility, EventSource, and audio paths were not exercised. |
| Signal Telegram preference and readiness API | Implemented | Unverified | Preference storage, state history, ownership, and readiness behavior were not exercised by a maintainer-requested pass. |
| Preset signal Telegram fan-out | Implemented | Unverified | Live occurrence dispatch, occurrence-time eligibility, bounded cursor recovery, and durable outbox-job creation are available; no runtime pass was requested. |
| Preset signal Telegram provider delivery | Implemented | Unverified | The notification worker validates, safety-checks, formats, and sends `telegram_preset_signal` jobs; per-occurrence delivery history is not exposed. |
| Historical-analysis run, dataset, and simulation boundaries | Implemented | Unverified | Owner-scoped request/lifecycle API, canonical coverage validation, immutable snapshots, fingerprinting, stale detection, and pure fixed-preset simulation; no worker, report, or browser analysis runtime exists. |

## Next Actions

1. Request a dedicated verification pass when the maintainer is ready.

## Handoff Constraints

- Follow the documentation ownership and status vocabulary in [docs/README.md](README.md).
- Read the target issue, approved solution, and relevant authoritative documents before changing behavior.
- Keep GitHub issues and pull requests as implementation history; do not add completed-work diaries.
- Update every affected authoritative document and replace stale statements in the same change.
- Keep README files to setup and navigation, with links to detailed owners.
- Preserve authenticated ownership, exact-decimal market data, immutable event/version semantics, and separation of occurrence from delivery.
- Keep provider credentials, session/CSRF tokens, and sensitive identifiers out of logs and documentation examples.
- Do not run verification commands unless the maintainer explicitly requests a verification pass; see [AGENTS.md](../AGENTS.md).
