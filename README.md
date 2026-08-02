# FreeCoinAlert

## What It Does Now

FreeCoinAlert is an informational cryptocurrency-alert application. Signed-in users can link a private Telegram destination, create one-time price-crossing alerts for a controlled Binance Spot catalogue, manage fixed preset-signal subscriptions, and review the authenticated historical/live signal feed in the browser. The feed has optional, user-activated in-page sound; it does not replace Telegram delivery.

## Current Scope

- Account sessions, CSRF protection, and browser sign-in/sign-up flows.
- Telegram linking, test-notification queueing, and durable notification processing.
- One-time exact-decimal price-crossing alerts for the supported Binance Spot markets.
- Canonical closed-candle storage, `1h`/`4h` aggregation, and fixed SMA 200 / RSI 14 preset evaluation.
- Read-only preset cards, authenticated subscription controls, paginated signal history, credentialed live updates, visibility recovery, and optional built-in sound.

See the authoritative [product overview](docs/PRODUCT.md) for capabilities, limits, planned work, and non-goals.

## Repository Layout

- [`apps/web`](apps/web) — Next.js browser application.
- [`apps/api`](apps/api) — FastAPI application and its runnable market, Telegram, and notification modules.
- [`docs`](docs) — authoritative current-state documentation.
- [`services`](services) and [`packages`](packages) — present as repository boundaries; they contain no standalone runnable components.

## Local Development

Use Node.js `24.18.0`, pnpm `11.4.0`, Docker Compose, CPython `3.14`, and uv. Copy [`.env.example`](.env.example) to `.env`, then install dependencies and start the local stack:

```bash
pnpm install
pnpm dev
```

Detailed configuration, process commands, and recovery guidance are in [OPERATIONS.md](docs/OPERATIONS.md).

## Common Commands

```bash
pnpm dev
pnpm dev:down
pnpm dev:market
pnpm dev:telegram
pnpm db:migrate
```

`pnpm dev:reset` removes local Compose volumes, including PostgreSQL data. See [OPERATIONS.md](docs/OPERATIONS.md) before using operational commands.

## Runtime Profiles

The default Compose stack starts the web app, API, and PostgreSQL. The `market` profile starts the Binance market stream; the `telegram` profile starts the Telegram poller and notification worker. See [OPERATIONS.md](docs/OPERATIONS.md) for entry points and provider-contact boundaries.

## Documentation

Start with the [Documentation Guide](docs/README.md). It identifies the sole detailed owner for each domain and the appropriate reading path.

## Current Availability and Verification

Current behavior is implemented in merged `main` but has not received a maintainer-requested runtime verification pass. Implemented does not mean verified; see [PRODUCT.md](docs/PRODUCT.md) and [CONTINUITY.md](docs/CONTINUITY.md).

## Safety Boundary

FreeCoinAlert provides informational alerts only. It does not execute trades, hold customer funds, request exchange API keys, provide financial advice, or guarantee alert delivery or investment outcomes.
