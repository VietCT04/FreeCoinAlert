# FreeCoinAlert Web

## Purpose

`apps/web` is the Next.js browser application for account access, a responsive authenticated dashboard shell, Telegram connection, one-time price-alert management, fixed preset subscriptions, the authenticated signal feed, and the authenticated historical-analysis flow.

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

- `/` — public entry point that redirects authenticated users to the dashboard.
- `/dashboard` — owner-scoped overview of active monitoring, Telegram readiness, catalogue readiness, and recent activity.
- `/price-alerts` — status-filtered one-time price-alert cards and an accessible create dialog.
- `/preset-signals` — filtered fixed-preset cards, server-confirmed subscription controls, Telegram-delivery switches, and a separate signal-history tab.
- `/historical-analysis` — bounded historical-analysis requests and reports.
- `/telegram` — private Telegram connection, test-notification, notification-usage, and disconnect controls.
- `/sign-in` — browser sign-in.
- `/sign-up` — browser registration.

The dashboard shell uses the existing opaque-cookie `AuthProvider` as its only authentication source. Its overview makes independent read-only requests to existing alert, subscription, Telegram, market-catalogue, and signal-feed endpoints; it does not poll, open SSE, or persist dashboard data in browser storage. Each feature route owns its existing hook lifecycle. Price alerts use the existing status-filtered endpoint with server-confirmed responsive cards and a dialog-based create flow. Preset signals use client-side display filters and mounted Presets/Signal history tabs so EventSource, replay recovery, and sound state are not restarted by tab changes. The signal surface uses native Fetch, EventSource, React state/effects, and the Web Audio API. Preset formulas and parameters remain server-controlled and read-only; browser sound is off by default and is never required for visual updates. Active preset cards also expose the server-owned Telegram-delivery preference and dynamic destination readiness. Telegram usage counts use existing owner-scoped reads and show each subsection as unavailable when its request fails.

Telegram-delivery controls use credentialed native Fetch and the existing CSRF token, confirm enabling, apply only successful server responses, and keep browser history and sound separate from provider delivery. The browser does not contact Telegram or store preference, readiness, destination, or token data in local storage.

The historical-analysis section uses credentialed native Fetch and the existing CSRF token for bounded run creation and cancellation. It polls selected queued/running runs only while the document is visible, presents server-provided assumptions and reports, and does not calculate indicators or metrics in the browser. Run IDs, reports, trades, equity points, fingerprints, and idempotency keys remain in memory only. In Compose, the web service waits for the API health check and carries no API, database, Telegram, or provider credentials.

The browser owns a shadcn/ui foundation under `src/components/ui`, shared presentational patterns under `src/components`, and dashboard-shell components under `src/components/dashboard`. It uses the approved New York-style neutral/zinc tokens, Lucide icons, Radix primitives, Recharts chart composition, and Sonner for non-sensitive success confirmations. The shell provides a collapsible desktop sidebar, mobile drawer navigation, breadcrumbs, a user menu, a theme toggle, skip navigation, and route-level safe loading/error boundaries without changing feature workflows.

## Accessibility Foundation

The repository-owned foundation and workflow surfaces provide keyboard-visible focus, semantic buttons, labels, alerts, dialogs, switches, tabs, tables, responsive overflow handling, active-route indication, skip navigation, `nav`/`header`/`main` landmarks, one page-level heading per route, status text alongside visual treatments, focus movement to signal history after `View history`, reduced-motion handling, and accessible chart alternatives through the existing table pattern. Preset tab contents remain mounted while inactive and are visually hidden so live-feed state is preserved. Theme selection supports light, dark, and system modes through one shared provider boundary. The dashboard and workflow redesign are implemented and remain unverified until a maintainer requests a browser or accessibility pass.

## Authoritative Documentation

- [Product](../../docs/PRODUCT.md)
- [API contracts](../../docs/API.md)
- [Security](../../docs/SECURITY.md)
- [Architecture](../../docs/ARCHITECTURE.md)
