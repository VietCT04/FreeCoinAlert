# Database

## Purpose

This document defines the initial data domains, schema rules, timestamp conventions, idempotency requirements, migration expectations, and unresolved storage decisions.

## Status

No application schema or migration exists yet.

Issue #7 provides PostgreSQL `18.4` as the local development database through the Compose service named `db`. It binds to `127.0.0.1:${POSTGRES_PORT:-5432}` and persists data in the Docker-managed `postgres_data` volume. This is a running database server only: no application connection, schema, migration, seed data, or backup automation exists.

PostgreSQL is the current database direction because the product requires relational ownership, durable jobs, uniqueness constraints, time-based market data, and transactional alert-event creation.

## Data Domains

The eventual schema is expected to cover:

- Users and user preferences
- Telegram connections and one-time linking tokens
- Supported exchanges, markets, symbols, and timeframes
- Signal templates and immutable template versions
- User alerts and custom rule definitions
- Alert evaluation state
- Alert events
- Notification outbox jobs and delivery attempts
- Canonical one-minute candles
- Market-data gaps and reconciliation runs
- Future historical-analysis jobs and results

Exact tables are created only through focused implementation issues.

## Global Rules

- Store timestamps in UTC.
- Prefer database-generated identifiers.
- Define ownership relationships explicitly.
- Add foreign keys unless a documented high-volume path requires another approach.
- Use migrations for every schema change.
- Never edit an already-applied production migration silently.
- Make externally driven writes idempotent.
- Keep status transitions explicit.
- Avoid storing secrets in plaintext.
- Document retention and deletion behavior before production launch.

## Canonical Candle Rule

One-minute closed candles are the canonical stored market-data interval.

The uniqueness rule must be equivalent to:

```text
(exchange, market_type, symbol, open_time)
```

If multiple intervals are stored later, include `interval` in the key.

Required candle fields are expected to include:

- Exchange
- Market type
- Symbol
- Open time
- Close time
- Open
- High
- Low
- Close
- Base volume
- Quote volume when available
- Trade count when available
- Ingestion or update timestamp

Numeric types and precision must be selected deliberately. Do not use binary floating-point storage for values that require exact decimal representation.

An unfinished candle must not overwrite a confirmed closed candle.

## Aggregated Candles

Larger timeframes should initially be derived from canonical one-minute candles.

Whether derived candles are persisted or computed depends on measured query and evaluation needs. The live and historical paths must share the same aggregation implementation regardless of persistence choice.

## Alert and Event Idempotency

Alert events need a reproducible deduplication key based on the trigger type.

A candle-close alert key should be equivalent to:

```text
user_alert_id + strategy_version + candle_open_time + trigger_identity
```

A price alert needs an explicit crossing-state model so repeated price events on the same side of a threshold do not create repeated alerts.

The database must prevent duplicate logical alert events when processing is retried.

## Notification Outbox

Creating an alert event and its notification job must occur in one transaction.

Expected outbox fields include:

- Alert event ID
- Channel
- Destination reference
- Status
- Attempt count
- Next attempt time
- Provider message identifier when available
- Last error category and safe message
- Created, claimed, sent, and updated timestamps

Workers must claim jobs safely so parallel workers do not send the same job concurrently.

## Telegram Linking Tokens

Linking tokens must be:

- Securely random
- Short-lived
- Single-use
- Bound to the authenticated user who requested them
- Invalidated after successful linking

Store a hash instead of the raw token where practical.

## Strategy Storage

Platform templates must be versioned.

A user alert referencing a platform template must remain pinned to a specific immutable version.

Custom rule definitions must be stored in a validated, deterministic, versioned format. Store the rule-schema version so migrations and historical reproduction remain possible.

## Indexing Direction

Likely access paths include:

- Active alerts by symbol, market, timeframe, and evaluation mode
- User alerts by user and status
- Alert events by user and trigger time
- Pending notification jobs by status and next-attempt time
- Candles by symbol and time range
- Missing candle ranges by symbol and date

Indexes must be justified by actual queries. Avoid speculative indexes that increase write cost without supporting known access patterns.

## Partitioning and Retention

Candle volume may become large. Before broad symbol ingestion, define:

- Supported symbol count
- Retention period
- Expected yearly row count
- Partitioning strategy
- Backup and restore implications
- Archival policy

Monthly time partitioning is a candidate, not an approved final design.

## Migration Rules

Before changing the schema:

1. Read this document and relevant domain docs.
2. Inspect existing models, migrations, indexes, constraints, and status values.
3. Make the smallest required change.
4. Add a migration.
5. Update shared schemas and API contracts if affected.
6. Document data migration, rollback, locking, and retention risks.
7. Update `CONCERNS.md` for meaningful unresolved risk.

## Pending Decisions

- Authentication-related schema based on the selected auth approach.
- Final table names and identifier types.
- Decimal precision for market values.
- Whether aggregated candles are persisted.
- Candle retention and partitioning.
- Backup frequency and recovery objectives.
- Data-deletion behavior for account removal.
