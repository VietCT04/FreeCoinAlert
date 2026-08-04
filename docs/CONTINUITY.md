# Continuity

## Current Snapshot

- Account sessions, CSRF protection, and browser authentication are implemented; see [SECURITY.md](SECURITY.md).
- Private Telegram linking, test notifications, and durable outbox processing are implemented; see [TELEGRAM.md](TELEGRAM.md).
- The controlled Binance Spot catalogue and singleton market stream are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- Closed `1m` candles and derived `1h`/`4h` candles are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- One-time price-crossing alerts and their browser management surface are implemented; see [ALERTS.md](ALERTS.md) and [PRODUCT.md](PRODUCT.md).
- Fixed SMA 200 and RSI 14 preset subscriptions and global occurrences are implemented; see [STRATEGIES.md](STRATEGIES.md) and [ALERTS.md](ALERTS.md).
- Per-subscription Telegram-delivery preference storage, immutable occurrence-time subscription state history, owner-scoped readiness responses, and the CSRF-protected preference API are implemented; the preference is disabled by default. Active preset cards provide server-confirmed enable/disable controls with confirmation for enabling, and returning to the preset-signals route refetches readiness without changing subscription state. New live occurrences also have durable dispatch rows, occurrence-time eligibility, bounded cursor fan-out, idempotent immutable-snapshot outbox jobs, database-only recovery, and notification-worker delivery with strict payload and send-time safety checks. See [API.md](API.md), [DATABASE.md](DATABASE.md), [ALERTS.md](ALERTS.md), and [TELEGRAM.md](TELEGRAM.md).
- The authenticated historical/live signal-feed API and SSE transport are implemented and Unverified; the authenticated browser preset catalog, subscription controls, Telegram-delivery controls, history feed, visibility recovery, and optional browser sound are implemented by the current frontend surface.
- The authenticated historical-analysis run API, canonical dataset preparation, immutable candle snapshots, pure deterministic fixed-preset simulation engine, bounded worker, immutable report persistence, owner-scoped report/trade/equity reads, explicit terminal-run cleanup, and authenticated browser Configure/Processing/Results flow are Implemented and Unverified. The browser includes responsive previous-run selection, report tabs, a server-owned Recharts preview, and accessible tables without client-side calculations. See [BACKTESTING.md](BACKTESTING.md), [DATABASE.md](DATABASE.md), and [MARKET_DATA.md](MARKET_DATA.md).
- The repository-owned shadcn/ui primitives, responsive dashboard shell, Overview route, dedicated feature routes, status-filtered price-alert cards/dialog, mounted preset tabs and filters, Telegram connection/test/usage/disconnect cards, card-based sign-in/sign-up, historical-analysis report tabs, owner-visible recent activity, New York-style neutral/zinc tokens, and light/dark/system theme boundary are Implemented and Unverified. The shell and workflow surfaces preserve existing feature behavior and API ownership. See [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), and the [web README](../apps/web/README.md).
- Local Compose orchestration is Implemented and Verified for the full-stack startup path: the persistent core waits for shared API preparation and migration, the `market` profile gates the stream behind catalog and bounded candle initialization, the `telegram` profile waits for migration, and the `historical-analysis` profile starts the real worker after migration. Broader recovery paths remain Unverified. See [OPERATIONS.md](OPERATIONS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
- The isolated E2E Compose environment, deterministic Binance/Telegram provider simulator, guarded canonical seed, internal fixture/control service, and historical-worker gate are Implemented and Unverified. The environment uses dedicated `_e2e` resources and is separate from normal local startup. See [TESTING.md](TESTING.md), [OPERATIONS.md](OPERATIONS.md), [MARKET_DATA.md](MARKET_DATA.md), and [TELEGRAM.md](TELEGRAM.md).
- The pinned Playwright workspace, desktop/mobile smoke projects, reusable fixtures and controls, dependency-free `pnpm e2e`/`pnpm e2e:ui`/`pnpm e2e:report` lifecycle, service-state checks, bounded logs, redacted artifacts, and teardown handling are Implemented and Unverified. Complete feature journey specifications remain Planned. See [TESTING.md](TESTING.md), [OPERATIONS.md](OPERATIONS.md), [SECURITY.md](SECURITY.md), and the [E2E workspace README](../apps/e2e/README.md).
- Local setup, one-command startup, readiness, status, logs, shutdown, and reset controls are Implemented and Unverified: the dependency-free Node entry point preserves an existing `.env`, validates the strict local contract, resolves enabled Compose profiles, waits for one-shot/health state, reports normalized statuses and local URLs, follows foreground logs, preserves volumes on shutdown, and requires explicit reset confirmation. See [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [OBSERVABILITY.md](OBSERVABILITY.md).

## Active Work

- Provider-worker delivery is implemented but does not expose per-occurrence delivery history.

## Current Blockers

- There is no current implementation blocker. A maintainer-requested browser and broader runtime verification pass remains outstanding.

See [CONCERNS.md](CONCERNS.md) for risks that do not block current work or safe operation.

## Verification Status

| Area | Availability | Verification | Note |
| --- | --- | --- | --- |
| Browser dashboard, account, authentication, and price alerts | Implemented | Unverified | The responsive shell, overview, card-based sign-in/sign-up, status filters, create dialog, and alert cards are available, but no explicit browser or end-to-end pass was requested. |
| Telegram linking and delivery | Implemented | Unverified | Provider and worker paths were not exercised. |
| Market data and candles | Implemented | Unverified | Binance catalogue/bootstrap and market-stream startup were exercised; maintenance, reconciliation, correction, and reconnect paths remain unverified. |
| Preset signal occurrences | Implemented | Unverified | Global occurrence evaluation and the authenticated feed boundary are available. |
| Signal history and live SSE | Implemented | Unverified | Durable history, cursor recovery, listener, and stream paths were not exercised. |
| Browser preset subscriptions, Telegram controls, and live feed | Implemented | Unverified | The preset tabs/filters, Telegram switches/usage cards, visibility, EventSource, and audio paths were not exercised. |
| Signal Telegram preference and readiness API | Implemented | Unverified | Preference storage, state history, ownership, and readiness behavior were not exercised by a maintainer-requested pass. |
| Preset signal Telegram fan-out | Implemented | Unverified | Live occurrence dispatch, occurrence-time eligibility, bounded cursor recovery, and durable outbox-job creation are available; no runtime pass was requested. |
| Preset signal Telegram provider delivery | Implemented | Unverified | The notification worker validates, safety-checks, formats, and sends `telegram_preset_signal` jobs; per-occurrence delivery history is not exposed. |
| Historical-analysis run, dataset, worker, report, series, and browser flow | Implemented | Unverified | Owner-scoped lifecycle API, canonical coverage validation, immutable snapshots, restart-safe worker/recovery, report publication, owner-only series reads, explicit cleanup, guided report tabs, Recharts preview, responsive run history, and visible-document polling; no runtime/browser pass was requested. |
| Local Compose initialization and profile dependency graph | Implemented | Verified | API preparation, migration gating, market catalogue/candle prerequisites, API/web health, market stream, and historical-analysis worker were exercised by the full-stack startup pass; Telegram was disabled. |
| Isolated E2E environment, simulator, seed, and controls | Implemented | Unverified | The dedicated overlay and guarded deterministic fixtures were inspected statically; no Compose or provider pass was requested. |
| Playwright workspace, runner, smoke projects, and safe artifacts | Implemented | Unverified | The pinned container, one-worker projects, lifecycle checks, redaction, and teardown are present; no browser or runner pass was requested. |
| Local setup and one-command lifecycle controls | Implemented | Unverified | Full-stack startup, readiness, status, and volume-preserving shutdown were exercised; setup/preflight, log following, and reset remain unverified. |

## Next Actions

1. Request dedicated isolated E2E, browser, Telegram-delivery, maintenance, and broader runtime verification when the maintainer is ready.

## Handoff Constraints

- Follow the documentation ownership and status vocabulary in [docs/README.md](README.md).
- Read the target issue, approved solution, and relevant authoritative documents before changing behavior.
- Keep GitHub issues and pull requests as implementation history; do not add completed-work diaries.
- Update every affected authoritative document and replace stale statements in the same change.
- Keep README files to setup and navigation, with links to detailed owners.
- Preserve authenticated ownership, exact-decimal market data, immutable event/version semantics, and separation of occurrence from delivery.
- Keep provider credentials, session/CSRF tokens, and sensitive identifiers out of logs and documentation examples.
- Do not run verification commands unless the maintainer explicitly requests a verification pass; see [AGENTS.md](../AGENTS.md).
