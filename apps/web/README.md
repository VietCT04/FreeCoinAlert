# FreeCoinAlert Web

## Purpose

`apps/web` is the Next.js browser application for account access, Telegram connection, one-time price-alert management, fixed preset subscriptions, and the authenticated signal feed.

## Prerequisites and Setup

Use Node.js `24.18.0` and pnpm `11.4.0`. Install workspace dependencies from the repository root:

```bash
pnpm install
```

For Compose, copy the root [`.env.example`](../../.env.example) to the ignored root `.env` and set `NEXT_PUBLIC_API_BASE_URL` there. For direct-host development, copy this component's [`.env.example`](.env.example) to the ignored `apps/web/.env.local` and set it there. The value must point to the API origin and must not contain a secret.

## Entry Points

Run these from the repository root:

```bash
pnpm dev:web
pnpm build:web
pnpm --filter @freecoinalert/web start
```

## Current Surfaces

- `/` — authenticated account, Telegram connection, price-alert, preset-subscription, and signal-history surface.
- `/sign-in` — browser sign-in.
- `/sign-up` — browser registration.

The root signal surface uses native Fetch, EventSource, React state/effects, and the Web Audio API. Preset formulas and parameters remain server-controlled and read-only; browser sound is off by default and is never required for visual updates.

Preset Telegram-delivery preferences are currently represented by the API contract but have no browser controls or message-delivery behavior in this application.

## Authoritative Documentation

- [Product](../../docs/PRODUCT.md)
- [API contracts](../../docs/API.md)
- [Security](../../docs/SECURITY.md)
- [Architecture](../../docs/ARCHITECTURE.md)
