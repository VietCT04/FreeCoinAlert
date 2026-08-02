# FreeCoinAlert Web

## Purpose

`apps/web` is the Next.js browser application for account access, Telegram connection, and one-time price-alert management.

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

- `/` — authenticated account, Telegram connection, and price-alert surface.
- `/sign-in` — browser sign-in.
- `/sign-up` — browser registration.

Preset-subscription controls and the signal feed are Planned; they are not browser surfaces yet.

## Authoritative Documentation

- [Product](../../docs/PRODUCT.md)
- [API contracts](../../docs/API.md)
- [Security](../../docs/SECURITY.md)
- [Architecture](../../docs/ARCHITECTURE.md)
