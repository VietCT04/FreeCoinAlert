# FreeCoinAlert Web

## Purpose

`apps/web` is the Next.js browser application for account access, Telegram connection, one-time price-alert management, fixed preset subscriptions, the authenticated signal feed, and the authenticated historical-analysis flow.

## Prerequisites and Setup

Use Node.js `24.18.0` and pnpm `11.4.0`. Install workspace dependencies from the repository root:

```bash
pnpm install
```

For Compose, run `pnpm dev:setup` from the repository root. It copies the root [`.env.example`](../../.env.example) to the ignored root `.env` only when needed and validates `NEXT_PUBLIC_API_BASE_URL` with the other local settings. `pnpm dev:preflight` repeats that validation without starting a process or contacting a provider. For direct-host development, copy this component's [`.env.example`](.env.example) to the ignored `apps/web/.env.local` and set it there. The browser-visible value must point to the API origin and must not contain a secret.

## Entry Points

Run these from the repository root:

```bash
pnpm dev:web
pnpm build:web
pnpm --filter @freecoinalert/web start
```

## Current Surfaces

- `/` — authenticated account, Telegram connection, price-alert, preset-subscription, signal-history, and historical-analysis surface.
- `/sign-in` — browser sign-in.
- `/sign-up` — browser registration.

The root signal surface uses native Fetch, EventSource, React state/effects, and the Web Audio API. Preset formulas and parameters remain server-controlled and read-only; browser sound is off by default and is never required for visual updates. Active preset cards also expose the server-owned Telegram-delivery preference and dynamic destination readiness.

Telegram-delivery controls use credentialed native Fetch and the existing CSRF token, confirm enabling, apply only successful server responses, and keep browser history and sound separate from provider delivery. The browser does not contact Telegram or store preference, readiness, destination, or token data in local storage.

The historical-analysis section uses credentialed native Fetch and the existing CSRF token for bounded run creation and cancellation. It polls selected queued/running runs only while the document is visible, presents server-provided assumptions and reports, and does not calculate indicators or metrics in the browser. Run IDs, reports, trades, equity points, fingerprints, and idempotency keys remain in memory only. In Compose, the web service waits for the API health check and carries no API, database, Telegram, or provider credentials.

## Authoritative Documentation

- [Product](../../docs/PRODUCT.md)
- [API contracts](../../docs/API.md)
- [Security](../../docs/SECURITY.md)
- [Architecture](../../docs/ARCHITECTURE.md)
