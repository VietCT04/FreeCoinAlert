# Testing and Verification

## Purpose

This document owns the current testing boundary, verification vocabulary, and isolated full-stack E2E environment. It does not claim that an E2E suite, provider simulator, or browser flow has been run.

## Verification Boundary

Static repository inspection is separate from runtime verification. `Verified` requires an explicit maintainer-requested verification pass. Tests, builds, migrations, services, providers, browser interaction, linting, formatting checks, type checks, documentation generators, and link checkers are not run during ordinary implementation unless that pass is explicitly requested. Each pull request states exactly what was and was not run.

The isolated environment in this document is separate from Playwright specifications, the E2E runner, root runner scripts, CI integration, and suite execution. Those follow-up concerns belong to issue #113. This issue provides the environment, simulator, deterministic fixtures, and internal controls that a later runner can consume.

## Isolated E2E Environment

`.env.e2e` is a committed test-only configuration and is never copied to `.env`. The runner invokes the fixed project and overlay exactly as follows:

```bash
docker compose \
  -p freecoinalert-e2e \
  --env-file .env.e2e \
  -f compose.yaml \
  -f compose.e2e.yaml
```

The environment uses database `freecoinalert_e2e`, named E2E-only volumes and network, and host ports `3100`, `8100`, and `55432`. The runner removes stale project resources before startup and removes the E2E volumes after the run. It never reads `.env`, reuses normal volumes, mounts the Docker socket, or exposes the provider simulator or control service on a host port.

The effective services are `db`, `api-prepare`, `db-migrate`, `provider-simulator`, `market-catalog-init`, `e2e-seed`, `api`, `web`, `market-stream`, `telegram-updates`, `notification-worker`, `signal-telegram-dispatcher`, `historical-analysis-worker`, and `e2e-control`. The API, web app, database, market processes, Telegram processes, and historical worker are the real application components. Only external providers and deterministic E2E fixtures are replaced.

The normal candle bootstrap is disabled. After migration and catalogue initialization, `e2e-seed` inserts fixed UTC, exact-decimal canonical history for every controlled market idempotently, including enough `1h` and `4h` rows to warm each fixed preset. The market stream and historical worker wait for that seed before processing. Browser scenarios use normal registration, login, ownership, CSRF, Telegram linking, alert, subscription, signal, and historical-analysis contracts; the seed does not create users.

## Provider Simulator

The Node simulator in `services/e2e-provider-simulator` has a pinned `ws` dependency, no database, and no production execution path. Binance REST supports exchange metadata and klines. The combined WebSocket supports deterministic aggregate-trade/ticker price events, open and closed one-minute klines, unavailable markets, and disconnect/reconnect controls. Telegram supports `getMe`, long-poll `getUpdates`, `sendMessage`, deterministic private `/start` linking, and sent, temporary, permanent, rate-limited, and uncertain outcomes. An uncertain send closes the connection so the worker records the safe unknown outcome.

Simulator mutations are internal and require `E2E_CONTROL_TOKEN`. Each mutation acknowledges a monotonically increasing sequence. A later runner waits for the business state after receiving the acknowledgement. The public simulator Telegram page records a browser visit and queues the private `/start` update; it is not a production Telegram endpoint.

## Guarded Seed, Control, and Worker Gates

`freecoinalert_api.e2e.seed`, `freecoinalert_api.e2e.control`, and `freecoinalert_api.e2e.worker_gate` refuse to run unless E2E mode is enabled and the configured database name ends in `_e2e`. The internal control service requires the E2E token, uses existing repositories and services, and only operates on already registered owner fixtures. It supports successful, zero-trade, pagination, terminal-failure, and historical-worker gate scenarios without creating users. No E2E control route is mounted in `freecoinalert_api.main`.

The historical-worker gate is test-only. With the gate disabled, production behavior is unchanged; with it enabled, a worker can be held at the pre-run boundary so a runner can exercise cancellation and release behavior.

## Safe Provider Configuration

Production Telegram API, Telegram file, and public bot URL defaults are `https://api.telegram.org/bot`, `https://api.telegram.org/file/bot`, and `https://t.me`. Custom Telegram URLs are rejected unless E2E mode is enabled. E2E mode requires the exact simulator endpoints at `provider-simulator`, requires `E2E_CLOCK_NOW` and `E2E_CONTROL_TOKEN`, and rejects an E2E database that does not end in `_e2e`. No production credentials are included in `.env.e2e`.

## Current Verification Status

The isolated E2E environment, simulator, deterministic seed, controls, and provider configuration are Implemented but Unverified. No Compose startup, migration, seed, provider, browser, test, build, package-install, lint, format, type-check, or other runtime verification was run for this change.
