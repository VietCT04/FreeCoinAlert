# FreeCoinAlert E2E Workspace

## Purpose

`apps/e2e` owns the repository Playwright configuration, reusable browser fixtures, provider/control clients, page-task helpers, bounded accessibility attachments, and authenticated feature-journey coverage for the current product routes. It runs inside the pinned Playwright container and exercises the real web application and API over the isolated Compose network, including historical-analysis worker lifecycles, provider recovery, mobile workflows, and stable accessibility states.

## Commands

Run these from the repository root:

```bash
pnpm e2e
pnpm e2e:ui
pnpm e2e:report
```

`pnpm e2e` validates the fixed E2E configuration, removes only the `freecoinalert-e2e` project and its volumes, builds the pinned images, starts the isolated stack, runs the desktop and mobile journeys, saves safe artifacts, and tears the stack down. `pnpm e2e:ui` keeps the same stack alive for Playwright UI mode and exposes only `127.0.0.1:9323`. `pnpm e2e:report` serves an existing HTML report without starting application services.

The normal runner does not install host browser binaries, read `.env`, accept an alternate Compose project or environment file, contact real providers, or require the normal local stack to be running.

## Workspace Layout

- `playwright.config.ts` — pinned desktop/mobile projects, timeouts, reporters, and failure artifacts.
- `fixtures/` — unique test users and reusable Playwright fixtures.
- `pages/` — user-task page helpers with assertions kept in specs.
- `support/` — provider/control clients, historical worker gates, business-state waits, accessibility checks, and redacted attachments.
- `specs/` — route-focused authentication, dashboard, Telegram, price-alert, preset-signal, historical-analysis, recovery, accessibility, and mobile journeys.
- `fixtures/historical-scenarios.ts` — versioned UTC ranges and server-display expectations for positive, negative, zero-trade, paginated, and missing-coverage worker scenarios. The isolated seed gives those named scenarios deterministic ETH, SOL, XRP, and BNB candle shapes while preserving the normal BTC seed pattern.

## Current Status

The workspace, fixtures, controls, feature specifications, and route coverage map are Implemented and Unverified. See [the E2E coverage matrix](../../docs/E2E_COVERAGE.md). No Playwright, browser, Compose, provider, build, or test verification pass has been run.
