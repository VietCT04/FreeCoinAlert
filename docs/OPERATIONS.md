# Operations

## Purpose

This document defines environment configuration, local startup, deployment portability, persistent data, backups, recovery, scheduling, release practices, and operational ownership.

## Current Direction

Hosting is intentionally undecided while the MVP is being built.

The project should run locally and remain portable between managed hosting and a low-cost VPS.

Target local startup:

```bash
docker compose up
```

This command is a target, not yet implemented.

## Repository Prerequisites and Commands

Repository-level tooling requires Node.js `24.18.0` LTS and pnpm `11.4.0`. The root pnpm workspace currently provides:

```bash
pnpm install
pnpm format
pnpm format:check
pnpm verify
```

`verify` currently checks root workspace formatting only. Issue #5 will add frontend checks, Issue #6 will add backend checks, and Issue #7 will add integrated local startup. `docker compose up` remains a later target owned by Issue #7.

## Environment Model

At minimum, support separate:

- Local development
- Automated test or CI
- Staging when introduced
- Production

Configuration must come from environment variables or an approved secret manager.

Do not hard-code:

- Database URLs
- Authentication secrets
- Telegram bot token
- Telegram webhook secret
- Binance endpoints when environment override is useful
- Public application URLs
- Provider-specific internal hostnames

Provide `.env.example` with variable names and safe descriptions only.

Shared variables belong in the root `.env.example` only when more than one application or service consumes them. Component-specific examples belong in `apps/<component>/.env.example` or `services/<component>/.env.example`. Never commit local `.env` files or real credentials.

## Process Model

The modular-monolith codebase may run as separate processes:

- Web frontend
- API
- Market-data worker
- Notification worker
- Scheduler or scheduled command
- Future historical-analysis worker

Early deployment may combine some processes in one container if lifecycle and failure behavior remain clear.

Do not combine expensive historical analysis with the real-time ingestion loop.

## Containers

Container expectations:

- Reproducible builds
- Pinned runtime versions
- Minimal runtime contents
- Non-root runtime user where practical
- Explicit health checks
- Graceful shutdown
- Restart policies
- No embedded secrets
- Multi-architecture support only when a selected host requires it

Persistent database data must not live only in an ephemeral application container.

## Networking

Publicly expose only required HTTP or HTTPS endpoints.

Do not expose:

- PostgreSQL directly to the internet unless protected by an approved network design
- Internal worker endpoints
- Debug ports
- Container-management sockets

Use TLS in production. A reverse proxy such as Caddy or Nginx may be selected when self-hosting.

## Scheduling

Scheduled responsibilities are expected to include:

- Daily candle reconciliation
- Controlled historical backfill commands or jobs
- Cleanup of expired Telegram linking tokens
- Retention cleanup when policies are defined
- Periodic data-quality checks

The selected scheduler must prevent uncontrolled duplicate concurrent runs.

Every scheduled job should be idempotent or protected by a safe locking strategy.

## Database Backups

Before production launch, define:

- Backup frequency
- Retention period
- Encryption
- Storage location
- Restore procedure
- Recovery point objective
- Recovery time objective
- Who verifies restore tests

A backup policy is incomplete until restoration is tested.

If using a managed database, document what the provider backs up and what remains the application's responsibility.

## Recovery Priorities

Suggested recovery order:

1. Protect database consistency.
2. Restore API access.
3. Restore market-data ingestion and detect the outage gap.
4. Reconcile missing candles.
5. Restore alert evaluation.
6. Restore notification delivery and process pending jobs safely.
7. Resume historical jobs last.

After a market-data outage, do not assume continuity. Detect and repair gaps before evaluating affected candle-close alerts.

## Deployment Provider Selection

Choose a provider only after measuring:

- CPU and memory usage
- WebSocket stability
- Database size and write rate
- Network egress
- Notification throughput
- Operational skill and maintenance time
- Required region and latency
- Backup and recovery options

Likely early options include managed application hosting or a small VPS. The application must not depend on one provider's proprietary behavior unless an approved issue accepts that coupling.

## Release Practices

Before production changes:

- Review database migrations.
- Verify environment variables.
- Run relevant build, lint, type, migration, or test checks according to project policy.
- Confirm rollback or forward-fix approach.
- Avoid deploying market-data schema changes without considering ingestion continuity.
- Record meaningful release and operational concerns.

## Graceful Shutdown

Processes should:

- Stop accepting new work.
- Finish or safely release claimed notification jobs.
- Close WebSocket and database connections.
- Persist required evaluation state.
- Resume safely without duplicate events after restart.

## Data Retention

Retention is not final.

Separate policies are needed for:

- One-minute candles
- Alert definitions
- Alert events
- Notification attempts
- Telegram connection data
- Audit logs
- Historical-analysis results

Retention changes require database, product, security, and operations review.

## Operational Runbooks Required Later

- Binance WebSocket disconnected
- Market data stale
- Candle gaps detected
- Binance REST rate limited or IP banned
- Telegram delivery backlog
- Telegram bot token exposed
- Database unavailable
- Disk nearly full
- Failed migration
- Restore from backup

## Pending Decisions

- Local Docker Compose topology.
- Initial hosting provider and region.
- Managed versus self-hosted PostgreSQL.
- Scheduler implementation.
- Backup and restore objectives.
- Deployment and rollback workflow.
- Domain, DNS, and TLS provider.
