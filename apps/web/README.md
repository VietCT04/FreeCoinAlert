# FreeCoinAlert Web

## Purpose

`apps/web` is the Next.js browser application for account access, Telegram connection, one-time price-alert management, fixed preset subscriptions, the authenticated signal feed, and the authenticated historical-analysis flow.

## Prerequisites and Setup

Use Node.js `24.18.0` and pnpm `11.4.0`. Install workspace dependencies from the repository root:

```bash
pnpm install
```

For Compose, run `pnpm dev:setup` and then `pnpm dev:all` from the repository root. Setup copies the root [`.env.example`](../../.env.example) to the ignored root `.env` only when needed; the full-stack wrapper validates `NEXT_PUBLIC_API_BASE_URL`, waits for API health, and prints the usable web/API URLs. `pnpm dev:preflight` repeats validation without starting a process or contacting a provider. For direct-host development, copy this component's [`.env.example`](.env.example) to the ignored `apps/web/.env.local` and set it there. The browser-visible value must point to the API origin and must not contain a secret.

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

The browser also owns a shadcn/ui foundation under `src/components/ui` and shared presentational patterns under `src/components`. It uses the approved New York-style neutral/zinc tokens, Lucide icons, Radix primitives, Recharts chart composition, and Sonner for non-sensitive success confirmations. This foundation establishes reusable boundaries without moving routes, migrating feature panels, or changing application behavior.

## Accessibility Foundation

The repository-owned foundation provides keyboard-visible focus, semantic buttons, labels, alerts, dialogs, tabs, tables, responsive overflow handling, status text alongside visual treatments, reduced-motion handling, and accessible chart alternatives through the existing table pattern. Theme selection supports light, dark, and system modes through one shared provider boundary. The foundation is implemented and remains unverified until a maintainer requests a browser or accessibility pass.

## Authoritative Documentation

- [Product](../../docs/PRODUCT.md)
- [API contracts](../../docs/API.md)
- [Security](../../docs/SECURITY.md)
- [Architecture](../../docs/ARCHITECTURE.md)
