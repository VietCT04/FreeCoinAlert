# FreeCoinAlert E2E Workspace

## Purpose

`apps/e2e` owns the repository Playwright configuration, reusable browser fixtures, provider/control clients, page-task helpers, accessibility attachments, and the minimal runner smoke coverage. It runs inside the pinned Playwright container and exercises the real web application and API over the isolated Compose network.

## Commands

Run these from the repository root:

```bash
pnpm e2e
pnpm e2e:ui
pnpm e2e:report
```

`pnpm e2e` validates the fixed E2E configuration, removes only the `freecoinalert-e2e` project and its volumes, builds the pinned images, starts the isolated stack, runs the desktop and approved mobile smoke projects, saves safe artifacts, and tears the stack down. `pnpm e2e:ui` keeps the same stack alive for Playwright UI mode and exposes only `127.0.0.1:9323`. `pnpm e2e:report` serves an existing HTML report without starting application services.

The normal runner does not install host browser binaries, read `.env`, accept an alternate Compose project or environment file, contact real providers, or require the normal local stack to be running.

## Workspace Layout

- `playwright.config.ts` — pinned desktop/mobile projects, timeouts, reporters, and failure artifacts.
- `fixtures/` — unique test users and reusable Playwright fixtures.
- `pages/` — user-task page helpers with assertions kept in specs.
- `support/` — provider/control clients, business-state waits, accessibility checks, and redacted attachments.
- `specs/` — the minimal runner smoke coverage; full feature journey specifications are not part of this implementation.

## Current Status

The workspace and runner are Implemented and Unverified. No Playwright, browser, Compose, provider, build, or test verification pass has been run.
