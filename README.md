# FreeCoinAlert

## What It Does Now

FreeCoinAlert is an informational cryptocurrency-alert application. Signed-in users can link a private Telegram destination, create one-time price-crossing alerts for a controlled Binance Spot catalogue, manage fixed preset-signal subscriptions, review the authenticated historical/live signal feed in the browser, and use the authenticated historical-analysis section to request and interpret bounded fixed-preset simulations. Historical-analysis runs are executed by a separate bounded database worker from canonical immutable datasets, and successful immutable reports expose owner-scoped summaries, trades, and equity series through the API and browser; no historical-analysis request contacts Binance or another provider. Signal subscriptions expose an explicit Telegram-delivery preference and dynamic readiness through the API and browser controls. Eligible live signal occurrences are fanned out into durable per-user Telegram outbox jobs with bounded recovery, and the notification worker can deliver those jobs through Telegram. The web app organizes authenticated work in a responsive dashboard shell with Overview, Price Alerts, Preset Signals, Historical Analysis, and Telegram routes. Historical analysis now presents a guided Configure, Processing, Results flow with responsive previous-run selection, report tabs, a server-provided Recharts equity preview, and an always-available table alternative. Sign-in and sign-up use the same server contracts in the shared card-based auth presentation. Browser and provider/runtime paths are unverified. The feed has optional, user-activated in-page sound; it does not replace Telegram delivery.

## Current Scope

- Account sessions, CSRF protection, and browser sign-in/sign-up flows.
- Telegram linking, test-notification queueing, and durable notification processing.
- One-time exact-decimal price-crossing alerts for the supported Binance Spot markets, with status-filtered cards and an accessible create dialog.
- Canonical closed-candle storage, `1h`/`4h` aggregation, and fixed SMA 200 / RSI 14 preset evaluation.
- Fixed preset cards grouped by timeframe, authenticated subscription and Telegram-delivery controls, separate tabbed signal history, paginated signal history, credentialed live updates, visibility recovery, and optional built-in sound.
- Owner-scoped signal Telegram-delivery preference storage and readiness API.
- Owner-scoped historical-analysis run/lifecycle API, bounded database worker, immutable report persistence, paginated trades/equity reads, explicit terminal-run cleanup, and the authenticated guided browser flow with report tabs, server-provided chart preview, and responsive run history.
- Occurrence-time signal fan-out into at-most-once-per-user durable Telegram outbox jobs and provider-worker delivery using immutable snapshots, bounded retries, and send-time safety checks.
- A responsive authenticated dashboard shell, Overview page, dedicated feature routes, status-aware price-alert cards, tabbed preset workflows, Telegram connection/usage cards, owner-visible recent activity, card-based authentication, historical-analysis report tabs, and light/dark/system theme selection using repository-owned UI primitives; feature workflows remain behaviorally unchanged.
- A pinned Playwright workspace with deterministic desktop/mobile feature-journey projects and a dependency-free isolated E2E runner that owns startup, safe failure artifacts, and teardown; the current route/action matrix is in [E2E_COVERAGE.md](docs/E2E_COVERAGE.md), and all browser/runtime behavior is Unverified.

See the authoritative [product overview](docs/PRODUCT.md) for capabilities, limits, planned work, and non-goals.

## Repository Layout

- [`apps/web`](apps/web) — Next.js browser application.
- [`apps/e2e`](apps/e2e) — pinned Playwright workspace and isolated feature-journey coverage.
- [`apps/api`](apps/api) — FastAPI application and its runnable market, Telegram, and notification modules.
- [`docs`](docs) — authoritative current-state documentation.
- [`services`](services) contains the isolated E2E provider simulator used only by the approved E2E Compose overlay; [`packages`](packages) remains a repository boundary with no standalone runnable component.

## Local Development

Use Node.js `24.18.0`, pnpm `11.4.0`, Docker Compose, CPython `3.14`, and uv. Install dependencies, create or validate the ignored local `.env`, and start the complete local MVP from the repository root:

```bash
pnpm install
pnpm dev:setup
pnpm dev:all
```

Detailed configuration, process commands, and recovery guidance are in [OPERATIONS.md](docs/OPERATIONS.md).

## Common Commands

```bash
pnpm dev:setup
pnpm dev:preflight
pnpm dev:all
pnpm dev:all:detached
pnpm dev:all:logs
pnpm dev:status
pnpm dev:down
pnpm dev:reset
pnpm dev:reset:force
pnpm e2e
pnpm e2e:ui
pnpm e2e:report
pnpm dev
pnpm dev:market
pnpm dev:telegram
pnpm dev:signal-telegram-dispatcher
pnpm db:migrate
```

`pnpm dev:setup` copies [`.env.example`](.env.example) only when `.env` is absent, never overwrites an existing file, and runs the local preflight. `pnpm dev:preflight` validates an existing configuration, Docker/Compose prerequisites, and local port availability without starting or stopping containers or contacting Binance or Telegram. `pnpm dev:all` reuses that preflight, starts the complete Compose topology, waits for initialization and health, prints the web/API readiness summary, and follows logs. `pnpm dev:all:detached` performs the same startup and readiness checks without following logs; `pnpm dev:all:logs` follows enabled full-stack logs. Telegram is disabled by default; enabling it requires the local username and token settings. The wrapper always selects `market`, conditionally selects `telegram`, and enables `historical-analysis` when the Compose model provides that profile.

## Isolated E2E Environment

The committed `.env.e2e` and `compose.e2e.yaml` provide a separate, deterministic full-stack environment for `pnpm e2e`. The runner uses project `freecoinalert-e2e`, dedicated named volumes and network, ports `3100`, `8100`, and `55432`, the internal provider simulator, guarded deterministic seed/control modules, and the pinned Playwright image. It is not part of normal `pnpm dev:all`; `pnpm e2e:ui` is the only mode that exposes the local Playwright UI at `127.0.0.1:9323`. See [TESTING.md](docs/TESTING.md), [OPERATIONS.md](docs/OPERATIONS.md), and the [E2E workspace README](apps/e2e/README.md).

`pnpm dev:reset` removes local Compose volumes, including PostgreSQL data, only after exact interactive `RESET` confirmation or the explicit `pnpm dev:reset:force` path. See [OPERATIONS.md](docs/OPERATIONS.md) before using operational commands.

## Runtime Profiles

`pnpm dev:all` starts PostgreSQL, prepares the shared API environment, applies migrations, starts the web/API core, always enables the `market` profile, enables `telegram` only when `LOCAL_ENABLE_TELEGRAM=true`, and enables `historical-analysis` when the Compose model provides it. The `market` profile synchronizes the controlled catalog and runs bounded candle bootstrap before the Binance market stream. The `telegram` profile starts the Telegram poller, notification worker, and signal fan-out dispatcher after migrations. The dispatcher does not contact Telegram; the notification worker delivers eligible preset-signal jobs when configured. The narrower `pnpm dev`, `pnpm dev:market`, and `pnpm dev:telegram` commands remain useful for component debugging. Browser Telegram-delivery controls use the existing authenticated API and do not contact the provider directly. See [OPERATIONS.md](docs/OPERATIONS.md) for entry points, dependency ordering, readiness, and provider-contact boundaries.

## Documentation

Start with the [Documentation Guide](docs/README.md). It identifies the sole detailed owner for each domain and the appropriate reading path.

## Current Availability and Verification

Current application behavior and the E2E runner are implemented in merged `main` but have not received a maintainer-requested browser/runtime verification pass. Implemented does not mean verified; see [PRODUCT.md](docs/PRODUCT.md), [TESTING.md](docs/TESTING.md), and [CONTINUITY.md](docs/CONTINUITY.md).

## Safety Boundary

FreeCoinAlert provides informational alerts only. It does not execute trades, hold customer funds, request exchange API keys, provide financial advice, or guarantee alert delivery or investment outcomes.
