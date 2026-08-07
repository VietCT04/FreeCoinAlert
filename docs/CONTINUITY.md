# Continuity

## Current Snapshot

- Account sessions, CSRF protection, and browser authentication are implemented; see [SECURITY.md](SECURITY.md).
- Private Telegram linking, test notifications, and durable outbox processing are implemented; see [TELEGRAM.md](TELEGRAM.md).
- The controlled Binance Spot catalogue and singleton market stream are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- Closed `1m` candles and derived `1h`/`4h` candles are implemented; see [MARKET_DATA.md](MARKET_DATA.md).
- One-time price-crossing alerts and their browser management surface are implemented; see [ALERTS.md](ALERTS.md) and [PRODUCT.md](PRODUCT.md).
- Fixed SMA 200 and RSI 14 preset subscriptions and global occurrences are implemented; see [STRATEGIES.md](STRATEGIES.md) and [ALERTS.md](ALERTS.md).
- Per-subscription Telegram-delivery preference storage, immutable occurrence-time subscription state history, owner-scoped readiness responses, and the CSRF-protected preference API are implemented; the preference is disabled by default. Active preset cards provide server-confirmed enable/disable controls with confirmation for enabling, and returning to the preset-signals route refetches readiness without changing subscription state. New live occurrences also have durable dispatch rows, occurrence-time eligibility, bounded cursor fan-out, idempotent immutable-snapshot outbox jobs, database-only recovery, and notification-worker delivery with strict payload and send-time safety checks. See [API.md](API.md), [DATABASE.md](DATABASE.md), [ALERTS.md](ALERTS.md), and [TELEGRAM.md](TELEGRAM.md).
- Local setup, one-command startup, readiness, status, logs, shutdown, and reset controls are Implemented and Unverified: the dependency-free Node entry point preserves an existing `.env`, validates the strict local contract, resolves enabled Compose profiles, waits for one-shot/health state, reports normalized statuses and local URLs, follows foreground logs, preserves volumes on shutdown, and requires explicit reset confirmation. See [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [OBSERVABILITY.md](OBSERVABILITY.md).
- The authenticated historical/live signal-feed API and SSE transport, including the covered browser history, replay, invalidation, visibility, and recovery paths, are Implemented and Verified through the isolated E2E pass; production provider behavior remains separate. See [API.md](API.md) and [ALERTS.md](ALERTS.md).
- The authenticated historical-analysis run API, canonical dataset preparation, immutable candle snapshots, pure deterministic fixed-preset simulation engine, bounded worker, immutable report persistence, owner-scoped report/trade/equity reads, explicit terminal-run cleanup, and authenticated browser Choose inputs/Run analysis/Results flow are Implemented. The existing API/worker scenarios are Verified by the isolated E2E pass; this presentation update is Unverified until a maintainer-requested pass. The browser includes responsive previous-run selection, three focused report tabs, and a server-owned Recharts preview without client-side calculations; full equity pagination remains an API capability and is not loaded by the report presentation. See [BACKTESTING.md](BACKTESTING.md), [DATABASE.md](DATABASE.md), and [MARKET_DATA.md](MARKET_DATA.md).
- The repository-owned shadcn/ui primitives, responsive dashboard shell, Overview route, dedicated feature routes, status-filtered price-alert cards/dialog, mounted preset tabs and filters, Telegram connection/test/usage/disconnect cards, card-based sign-in/sign-up, historical-analysis report tabs, owner-visible recent activity, New York-style neutral/zinc tokens, and light/dark/system theme boundary are Implemented and Verified for the existing covered browser journeys. The historical-analysis presentation update is Unverified until a maintainer-requested pass. The shell and workflow surfaces preserve existing feature behavior and API ownership. See [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), and the [web README](../apps/web/README.md).
- Local Compose orchestration is Implemented and Verified for the full-stack startup path: the persistent core waits for shared API preparation and migration, the `market` profile gates the stream behind catalog and bounded candle initialization, the `telegram` profile waits for migration, and the `historical-analysis` profile starts the real worker after migration. The isolated E2E startup, worker gates, recovery, and teardown paths are also Verified; maintenance, reset, and production recovery remain Unverified. See [OPERATIONS.md](OPERATIONS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
- The isolated E2E Compose environment, deterministic Binance/Telegram provider simulator, guarded canonical seed, internal fixture/control service, and historical-worker gates are Implemented and Verified by the full 65-case pass. The environment uses dedicated `_e2e` resources and is separate from normal local startup. See [TESTING.md](TESTING.md), [OPERATIONS.md](OPERATIONS.md), [MARKET_DATA.md](MARKET_DATA.md), and [TELEGRAM.md](TELEGRAM.md).
- The pinned Playwright workspace, desktop/mobile feature-journey projects, reusable fixtures and controls, named real-worker historical scenarios, queued/running worker gates, provider/feed recovery journeys, bounded accessibility attachments, dependency-free `pnpm e2e`/`pnpm e2e:ui`/`pnpm e2e:report` lifecycle, service-state checks, bounded logs, redacted artifacts, teardown handling, and the route/action coverage map are Implemented. The existing full pass verified the prior browser surface; the current historical-analysis selector updates are Unverified until a maintainer-requested pass. See [TESTING.md](TESTING.md), [OPERATIONS.md](OPERATIONS.md), [SECURITY.md](SECURITY.md), and the [E2E workspace README](../apps/e2e/README.md).
- Local setup, one-command startup, readiness, status, logs, shutdown, and reset controls are Implemented and Unverified: the dependency-free Node entry point preserves an existing `.env`, validates the strict local contract, resolves enabled Compose profiles, waits for one-shot/health state, reports normalized statuses and local URLs, follows foreground logs, preserves volumes on shutdown, and requires explicit reset confirmation. See [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [OBSERVABILITY.md](OBSERVABILITY.md).
- Local setup, one-command startup, readiness, status, logs, shutdown, and reset controls are Implemented and Unverified: the dependency-free Node entry point preserves an existing `.env`, validates the strict local contract, resolves enabled Compose profiles, waits for one-shot/health state, reports normalized statuses and local URLs, follows foreground logs, preserves volumes on shutdown, and requires explicit reset confirmation. See [OPERATIONS.md](OPERATIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [OBSERVABILITY.md](OBSERVABILITY.md).

## Active Work

- Provider-worker delivery is implemented but does not expose per-occurrence delivery history.

## Current Blockers

- There is no current implementation blocker. Production-provider, maintenance, reset, and broader deployment verification remain outside the isolated E2E pass.

See [CONCERNS.md](CONCERNS.md) for risks that do not block current work or safe operation.

## Verification Status

| Area | Availability | Verification | Note |
| --- | --- | --- | --- |
| Browser dashboard, account, authentication, and price alerts | Implemented | Verified | The responsive shell, overview, card-based sign-in/sign-up, status filters, create dialog, alert cards, and corresponding browser journeys passed the isolated E2E suite. |
| Telegram linking and delivery | Implemented | Verified | Linking, poller, worker, and simulator-backed delivery paths passed; real provider/device receipt remains unverified. |
| Market data and candles | Implemented | Verified | Simulator-backed catalogue/bootstrap, canonical seed, market stream, and disconnect/reconnect selection paths passed; Binance maintenance, reconciliation, correction, and production behavior remain unverified. |
| Preset signal occurrences | Implemented | Verified | Global occurrence evaluation, owner-visible history, invalidation, and the authenticated feed boundary passed in the isolated suite. |
| Signal history and live SSE | Implemented | Verified | Durable history, cursor recovery, listener, replay, reset, invalidation, and authentication-expiry paths passed. |
| Browser preset subscriptions, Telegram controls, and live feed | Implemented | Verified | The preset tabs/filters, Telegram switches/usage cards, visibility, EventSource, audio paths, and corresponding browser journeys passed. |
| Signal Telegram preference and readiness API | Implemented | Verified | Preference storage, state history, ownership, readiness, and covered mutation flows passed through the isolated API/browser paths. |
| Preset signal Telegram fan-out | Implemented | Verified | Live occurrence dispatch, occurrence-time eligibility, bounded cursor recovery, and durable outbox-job creation passed against the simulator-backed stack. |
| Preset signal Telegram provider delivery | Implemented | Verified | The notification worker validation, safety checks, formatting, and simulator sends passed; real provider behavior and per-occurrence history remain unverified. |
| Historical-analysis run, dataset, worker, report, series, and browser flow | Implemented | Unverified | Existing owner-scoped lifecycle, canonical coverage validation, immutable snapshots, worker cancellation/recovery, report publication, owner-only series reads, explicit cleanup behavior, focused report tabs, chart-only equity preview, responsive run history, and named real-worker scenarios passed; the current presentation update awaits a maintainer-requested pass. |
| Local Compose initialization and profile dependency graph | Implemented | Verified | API preparation, migration gating, market catalogue/candle prerequisites, API/web health, market stream, and historical-analysis worker were exercised by the full-stack startup and isolated E2E passes; Telegram used the simulator in E2E. |
| Isolated E2E environment, simulator, seed, and controls | Implemented | Verified | The dedicated overlay, guarded deterministic fixtures, named historical scenarios, worker gates, and owner-scoped signal invalidation passed the full Compose-backed suite. |
| Playwright workspace, runner, feature projects, coverage map, and safe artifacts | Implemented | Unverified | The pinned container, one-worker desktop/mobile projects, lifecycle checks, redaction, bounded accessibility attachments, teardown, fixtures, and route/action matrix passed the previous full run; current Historical Analysis selector updates await a maintainer-requested pass. |
| Local setup and one-command lifecycle controls | Implemented | Unverified | Full-stack startup and E2E lifecycle were exercised; setup/preflight, log following, volume-preserving shutdown outside the E2E runner, and reset remain unverified. |

## Next Actions

1. Request dedicated real-provider, maintenance, reset, deployment-recovery, and broader runtime verification when the maintainer is ready.

## Handoff Constraints

- Follow the documentation ownership and status vocabulary in [docs/README.md](README.md).
- Read the target issue, approved solution, and relevant authoritative documents before changing behavior.
- Keep GitHub issues and pull requests as implementation history; do not add completed-work diaries.
- Update every affected authoritative document and replace stale statements in the same change.
- Keep README files to setup and navigation, with links to detailed owners.
- Preserve authenticated ownership, exact-decimal market data, immutable event/version semantics, and separation of occurrence from delivery.
- Keep provider credentials, session/CSRF tokens, and sensitive identifiers out of logs and documentation examples.
- Do not run verification commands unless the maintainer explicitly requests a verification pass; see [AGENTS.md](../AGENTS.md).
