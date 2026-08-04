# Testing and Verification

## Purpose

This document owns the current testing boundary, verification vocabulary, isolated full-stack E2E environment, Playwright workspace, and repository runner. It does not claim that the E2E stack, provider simulator, browser, or feature-journey suite has been run.

## Verification Boundary

Static repository inspection is separate from runtime verification. `Verified` requires an explicit maintainer-requested verification pass. Tests, builds, migrations, services, providers, browser interaction, linting, formatting checks, type checks, documentation generators, and link checkers are not run during ordinary implementation unless that pass is explicitly requested. Each pull request states exactly what was and was not run.

## Isolated E2E Environment

`.env.e2e` is a committed test-only configuration and is never copied to `.env`. The runner owns the fixed Compose prefix:

```bash
docker compose \
  -p freecoinalert-e2e \
  --env-file .env.e2e \
  -f compose.yaml \
  -f compose.e2e.yaml
```

The environment uses database `freecoinalert_e2e`, named E2E-only volumes and network, and host ports `3100`, `8100`, and `55432`. The browser container uses the internal `web:3000` and `api:8000` service addresses and the matching internal CORS origin; the host-facing values remain fixed in `.env.e2e` for explicit local inspection. The runner never reads `.env`, reuses normal volumes, mounts the Docker socket, or exposes the provider simulator or control service on a host port.

The required application services are `db`, `api-prepare`, `db-migrate`, `provider-simulator`, `market-catalog-init`, `e2e-seed`, `api`, `web`, `market-stream`, `telegram-updates`, `notification-worker`, `signal-telegram-dispatcher`, `historical-analysis-worker`, and `e2e-control`. `e2e-tests` is built separately and run on demand after those services are ready. The API, web app, database, market processes, Telegram processes, and historical worker are the real application components. Only external providers and deterministic E2E fixtures are replaced.

The normal candle bootstrap is disabled. After migration and catalogue initialization, `e2e-seed` inserts fixed UTC, exact-decimal canonical history for every controlled market idempotently, including enough `1h` and `4h` rows to warm each fixed preset. The market stream and historical worker wait for that seed before processing. Browser scenarios use normal registration, login, ownership, CSRF, Telegram linking, alert, subscription, signal, and historical-analysis contracts; the seed does not create users.

## Playwright Workspace

The `apps/e2e` workspace pins `@playwright/test` to `1.62.0`, uses `mcr.microsoft.com/playwright:v1.62.0-noble`, and pins `@axe-core/playwright` to `4.12.1`. The package and image versions must remain equal for Playwright. The image activates pnpm `11.4.0`, uses the repository lockfile, runs trusted repository tests only, and sets `init: true` and `ipc: host` in Compose. Browser binaries are never installed on the developer host by the E2E commands.

The configuration has two deterministic projects:

- `chromium-desktop` runs all non-mobile feature specifications at `1440×900`.
- `chromium-mobile` uses the pinned Playwright `Pixel 7` Chromium descriptor and runs only `*.mobile.spec.ts` files.

Both projects use one worker, no retries, UTC, `en-US`, a 10-second action/expect timeout, a 20-second navigation timeout, and a 60-second test timeout. Historical-analysis specifications use a 120-second test timeout. No test may use `page.waitForTimeout()`.

The reusable fixture boundary supplies unique run/test-derived users, authenticated browser setup, provider-simulator controls, guarded E2E controls, business-state waits, page-task helpers, and accessibility result collection. Authentication tests register and sign in through the UI. Other feature tests may create an owner through Playwright `APIRequestContext` and transfer only the returned session cookie into a browser context. Tests never access PostgreSQL directly, intercept or fulfill FreeCoinAlert API requests, or call real providers. The current workspace contains feature specifications for authentication, dashboard, Telegram, one-time price alerts, preset signals, historical analysis, recovery, stable accessibility states, and mobile workflows; the route/action matrix is [E2E_COVERAGE.md](E2E_COVERAGE.md).

Selectors prefer accessible roles and names, associated labels, stable visible text, and only then an approved `data-testid` for dynamic content with no unique semantic selector. Page helpers represent user tasks; assertions remain in spec files. Helpers wait for visible business states or URL transitions and do not use arbitrary sleeps.

## Provider and E2E Controls

The Node simulator in `services/e2e-provider-simulator` provides deterministic Binance REST/combined WebSocket and Telegram contracts. Its internal mutations require `E2E_CONTROL_TOKEN` and acknowledge a monotonically increasing sequence. The guarded `e2e-control` service provides the versioned historical scenarios `analysis-positive`, `analysis-negative`, `analysis-zero-trade`, `analysis-paginated`, and `analysis-missing-coverage`, before-claim/after-claim worker gates, Telegram-link expiry, high-volume alert/signal-feed pagination fixtures, and owner-scoped signal invalidation. Historical success/failure/cancellation assertions use normal API reads after the real worker processes the fixture; the browser never calculates report values. Tests use the simulator for provider events and delivery outcomes, the control service only for those bounded fixture operations, and normal UI/API contracts for owner records; they do not create fixture users through internal controls.

## Runner Lifecycle

`pnpm e2e` is the only normal command required for the isolated full-stack E2E lifecycle. The dependency-free `scripts/e2e.mjs` runner uses Node built-ins and argument arrays with `shell: false`. It performs these actions in order:

1. Verify Node satisfies the repository `24.18.0 <= version < 25` engine.
2. Verify Docker Engine, Compose v2, and the fixed Compose configuration.
3. Parse `.env.e2e` without shell evaluation.
4. Reject Binance and Telegram URLs whose hostname is not exactly `provider-simulator`.
5. Require the `_e2e` database and distinct ports different from normal defaults.
6. Remove stale `freecoinalert-e2e` resources with `down --volumes --remove-orphans`.
7. Recreate only the fixed `artifacts/e2e` directory.
8. Build the provider simulator, real application images, E2E control service, and pinned Playwright image.
9. Start the required application services detached with `up --detach --wait --wait-timeout 300`.
10. Inspect completed, healthy, and running service states before any browser starts.
11. Run `docker compose ... run --rm e2e-tests pnpm exec playwright test`.
12. Preserve the Playwright exit code and return non-zero for startup, state, or test failure.
13. On startup or test failure, capture the latest 1,000 timestamped, no-colour log lines per E2E service.
14. Write `run-summary.json` with only service names/states, test counts, timestamps, and exit code.
15. Always run `down --volumes --remove-orphans`, including failure and interruption paths.
16. Keep cleanup idempotent and attempt it after both normal and forced child termination.

`pnpm e2e:ui` uses the same safety checks and stack, runs `playwright test --ui --ui-host=0.0.0.0 --ui-port=9323`, and exposes only `127.0.0.1:9323`. It keeps the stack alive until the UI process exits or receives Ctrl+C. `pnpm e2e:report` serves an existing HTML report only and does not start application services; it fails clearly when no report exists.

## Artifacts and Redaction

The runner binds the fixed Git-ignored host directory `artifacts/e2e/` and retains:

```text
artifacts/e2e/
├── playwright-report/
├── test-results/
├── results.json
├── compose-logs/
└── run-summary.json
```

Playwright uses screenshots only on failure, traces retained on failure, failure-only videos, and `line`, `html`, and `json` reporters. The custom attachment helper redacts keys matching `password`, `cookie`, `csrf`, `token`, `authorization`, `telegramChatId`, and `telegramUserId`. Storage-state files, request headers, cookies, CSRF tokens, passwords, Telegram tokens, provider secrets, and complete private API payloads are not attached. The runner does not accept an arbitrary artifact path and removes only the previous contents of the fixed repository directory.

## Required Service States

Completed successfully:

```text
api-prepare
db-migrate
market-catalog-init
e2e-seed
```

Healthy:

```text
db
provider-simulator
api
web
e2e-control
```

Running:

```text
market-stream
telegram-updates
notification-worker
signal-telegram-dispatcher
historical-analysis-worker
```

The runner does not print a ready state when any required service is unhealthy, restarting, dead, unexpectedly exited, or otherwise outside its required state.

## Current Availability and Verification

| Area | Availability | Verification |
| --- | --- | --- |
| Isolated E2E environment, simulator, seed, controls, and worker gate | Implemented | Unverified |
| Playwright workspace, pinned image, fixtures, helpers, and feature projects | Implemented | Unverified |
| Dependency-free E2E lifecycle runner and safe artifacts | Implemented | Unverified |
| Complete feature journey suite and route coverage map | Implemented | Unverified |

No Compose startup, migration, seed, provider, browser, Playwright, build, package-install, lint, format, type-check, or other runtime verification was run for this change.
