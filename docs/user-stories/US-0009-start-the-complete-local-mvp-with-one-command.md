# US-0009: Start the Complete Local MVP with One Command

## User Story

As a developer, I want to start the complete FreeCoinAlert application locally with one command, so that I can test every implemented user journey without manually starting or initializing individual services.

## Context

FreeCoinAlert currently has multiple local runtime components:

- PostgreSQL
- Database migrations
- FastAPI API
- Next.js web application
- Controlled Binance Spot market catalogue
- Candle history and live market stream
- Telegram update poller
- Signal Telegram dispatcher
- Notification worker
- Signal-feed listener inside the API process
- Historical-analysis API, dataset preparation, and pure simulation engine

The default local command starts only PostgreSQL, the API, and the web application. Market and Telegram processes require separate Compose profiles or commands, while first-run catalogue and candle initialization require manual operator knowledge. Historical-analysis execution must join the local stack only after its real worker exists.

The target experience is:

```text
pnpm dev:setup
pnpm dev:all
```

`dev:setup` is required only for the initial environment template. Every later startup should require only `pnpm dev:all`.

## Acceptance Criteria

- [ ] A developer can start every currently runnable local MVP component with `pnpm dev:all`.
- [ ] The full local stack uses one PostgreSQL database and one consistent environment configuration.
- [ ] Database migration completes before dependent application and worker processes start.
- [ ] The controlled market catalogue is initialized before market-dependent services are considered ready.
- [ ] Missing candle history is initialized through a bounded, restart-safe process.
- [ ] Sufficient existing history is preserved and does not trigger a full provider download on every restart.
- [ ] Web, API, market stream, Telegram poller, signal dispatcher, and notification worker are wired together without separate manual startup commands.
- [ ] The historical-analysis worker is included automatically only after Issue #82 provides a real runnable worker.
- [ ] Telegram can be explicitly disabled for local use when credentials are unavailable, while non-Telegram functionality remains usable.
- [ ] Telegram-enabled startup fails early and safely when required configuration is absent or invalid.
- [ ] Required initialization or service failure cannot produce a false ready message.
- [ ] Successful startup prints the web URL, API URL, health URL, and a concise component-status summary.
- [ ] Foreground startup handles Ctrl+C cleanly and preserves persistent database data.
- [ ] A detached startup, combined logs, full-stack status, safe shutdown, and explicitly destructive reset are available through repository commands.
- [ ] Local setup never overwrites an existing `.env`, prints secret values, or stores provider credentials in browser-visible configuration.
- [ ] First-run and normal local usage work from the repository root on supported developer operating systems.
- [ ] README and operations documentation present one primary local startup workflow rather than requiring profile discovery.
- [ ] All affected current-state documentation is updated with each implementation change.

## Desired Local Commands

```text
pnpm dev:setup
pnpm dev:all
pnpm dev:all:detached
pnpm dev:all:logs
pnpm dev:status
pnpm dev:down
pnpm dev:reset
```

`dev:reset` is destructive local data removal and must require an explicit warning and confirmation or a deliberate force option.

## Startup Principles

### One Primary Path

The root README should direct local developers to one setup command and one normal startup command. Narrow component commands may remain for debugging but are not the primary MVP workflow.

### Explicit Initialization Graph

Migration, catalogue initialization, and candle-history initialization are one-shot prerequisites. Long-running processes must depend on their successful completion instead of racing startup.

### Restart Safety

Restarting the full stack must preserve volumes, avoid duplicate logical records, and skip expensive initialization work when existing state is already sufficient.

### Honest Optional Components

Telegram services are either enabled with valid configuration or explicitly disabled. Unconfigured Telegram must not make unrelated local functionality unusable or be reported as running.

An unimplemented historical-analysis worker must be reported as unavailable. The orchestration must not create a placeholder process or claim completed report execution before Issue #82 exists.

### Readiness, Not Container Creation

A ready message means required initialization completed and required long-running services passed their local health/readiness checks. Merely creating containers is not sufficient.

## Out of Scope

- Production deployment or production images
- Domains, HTTPS, reverse proxies, or cloud hosting
- Kubernetes or distributed infrastructure
- CI/CD deployment
- Backups or production restore procedures
- Metrics dashboards or production alerting
- Automated browser/end-to-end verification
- Provider mocks or fake Telegram delivery
- Installing developer prerequisites
- Changing alerts, signals, Telegram, market-data, or historical-analysis product semantics

## Risks

- Incorrect Compose dependencies can start consumers before migrations or seed data exist.
- Re-running bootstrap blindly can waste provider capacity and delay every local restart.
- Optional Telegram configuration can make one-command startup brittle unless enablement is explicit.
- A wrapper can report success while a required container is unhealthy or a one-shot service failed.
- Cross-platform scripts can work on one shell while failing on Windows or another supported environment.
- A destructive reset command can remove local data accidentally without an explicit guard.
- Historical-analysis API requests can remain queued until the real worker from Issue #82 is implemented and included.

## Follow-up Issues

- #89 — Orchestrate the complete local MVP with Docker Compose
- #90 — Add safe local setup and provider preflight
- #91 — Add one-command readiness, logs, and shutdown controls

Implementation order:

```text
#89 → #90 → #91
```

Issue #89 may integrate the historical-analysis worker only after Issue #82 has merged and exposed the approved process entry point.

Each implementation issue requires an explicitly approved technical solution comment before work begins.
