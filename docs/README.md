# Documentation Guide

This directory contains the source-of-truth documentation for FreeCoinAlert.

Code and documentation must remain synchronized. Before changing a subsystem, read the corresponding document. When behavior, contracts, data, security, reliability, or product scope changes, update the relevant document in the same pull request.

## Recommended Reading Order

1. [`PRODUCT.md`](PRODUCT.md) — understand the user problem, MVP, boundaries, and success criteria.
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — understand components, ownership, and main data flows.
3. Read the domain document for the area being changed.
4. [`CONCERNS.md`](CONCERNS.md) — review unresolved risks and decisions.
5. [`CONTINUITY.md`](CONTINUITY.md) — review current state and next work.
6. Root [`AGENTS.md`](../AGENTS.md) — follow mandatory implementation and GitHub workflow rules.

## Document Catalog

| Document | Purpose | Update when |
|---|---|---|
| [`PRODUCT.md`](PRODUCT.md) | Product users, goals, MVP scope, non-goals, and success criteria | User-visible behavior or product scope changes |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System boundaries, components, data flows, and scaling principles | Components, responsibilities, or integration patterns change |
| [`API.md`](API.md) | API conventions, authentication behavior, resources, and contracts | An endpoint, request, response, error, or authorization rule changes |
| [`DATABASE.md`](DATABASE.md) | Data domains, schema rules, migrations, indexes, retention, and idempotency | A table, column, enum, index, partition, relationship, or retention rule changes |
| [`SECURITY.md`](SECURITY.md) | Threat model, authentication, authorization, secrets, abuse prevention, and safe custom rules | Security boundaries, permissions, sensitive data, or external credentials change |
| [`MARKET_DATA.md`](MARKET_DATA.md) | Binance ingestion, candle storage, aggregation, reconciliation, backfill, and rate limits | Market-data sources, timestamps, intervals, ingestion, or data-quality rules change |
| [`ALERTS.md`](ALERTS.md) | Alert lifecycle, evaluation modes, state, cooldowns, events, and deduplication | Alert behavior or trigger semantics change |
| [`TELEGRAM.md`](TELEGRAM.md) | Telegram linking, bot updates, destinations, delivery, retries, and disconnect behavior | Telegram integration or notification behavior changes |
| [`STRATEGIES.md`](STRATEGIES.md) | Signal templates, custom-rule format, indicators, operators, shared calculations, and versioning | Strategy definitions or evaluation behavior changes |
| [`BACKTESTING.md`](BACKTESTING.md) | Future historical simulation rules, trade assumptions, metrics, and bias prevention | Historical analysis or performance-report behavior changes |
| [`OPERATIONS.md`](OPERATIONS.md) | Configuration, deployment, backups, recovery, provider portability, and runbooks | Deployment topology or operational procedures change |
| [`OBSERVABILITY.md`](OBSERVABILITY.md) | Logs, metrics, health checks, freshness, alert delivery, and incident signals | Monitoring or service-health semantics change |
| [`CONCERNS.md`](CONCERNS.md) | Unresolved risks, assumptions, trade-offs, and decisions requiring review | Any meaningful uncertainty remains |
| [`CONTINUITY.md`](CONTINUITY.md) | Handoff state, completed work, active work, concerns, and next steps | Every meaningful change |
| [`user-stories/README.md`](user-stories/README.md) | User-story format, numbering, and conversion into focused GitHub Issues | Product planning workflow changes |

## Documentation Status

These documents establish initial decisions and boundaries. Final API contracts, schemas, infrastructure choices, supported symbols, retention periods, and strategy definitions must be introduced through focused GitHub Issues and pull requests.

Do not treat a `Pending` section as permission to invent behavior silently. Record the decision in the relevant issue, update the document, and then implement it.