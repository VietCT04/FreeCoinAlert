# Architecture

## Purpose

## Signal catalog boundary

The API owns the versioned signal-preset catalog and subscription lifecycle. Route handlers enforce session and CSRF boundaries, the subscription service coordinates validation and transactions, and repositories encapsulate preset/subscription persistence. No indicator engine, market-data provider work, WebSocket feed, or Telegram path is introduced by this boundary.

This document defines the initial system boundaries, component responsibilities, primary data flows, and architectural constraints for FreeCoinAlert.

## One-Time Price Alert Persistence Boundary

Issue #29 adds SQLAlchemy models and repositories for durable one-time price alerts and immutable
trigger events. The repository boundary creates, reads, locks, updates lifecycle and crossing state,
and records the single trigger event; it does not parse HTTP requests, validate CSRF, subscribe to
Binance, evaluate a crossing, send Telegram messages, or commit a coordinating transaction.

Future Issue #30 owns the alert API, Issue #31 owns the centralized live-price source, and Issue #32
owns locked evaluation plus atomic alert-event and notification-outbox creation.

## Architectural Style

Start as a modular monolith with separately runnable processes where needed.

The first implementation should avoid independent microservices unless operational measurements show a clear reason to split them. Code boundaries should still make future separation possible.

## Proposed Repository Boundaries

```text
apps/
├── web/                   # Browser application
└── api/                   # HTTP API and authentication boundary

services/
├── market-data/           # Binance streams, candle persistence, aggregation, repair
└── notifications/         # Notification outbox processing and Telegram delivery

packages/
├── shared/                # DTOs, schemas, enums, constants, API contracts
└── strategy-core/         # Aggregation, indicators, conditions, and evaluation
```

Directories should be created only when an approved issue requires them.

The repository uses native pnpm workspaces for JavaScript and TypeScript workspace management. It does not use Nx or Turborepo.

- `apps/` owns deployable browser and API applications. `apps/web` is the Next.js TypeScript frontend; `apps/api` is the FastAPI Python backend created by Issue #6.
- `services/` owns separately runnable background processes such as market-data ingestion and notification delivery.
- `packages/` owns reusable code that is not independently deployed.
- `packages/shared/` is reserved for concrete shared contracts when an approved issue first requires them.

The workspace currently establishes only these boundaries. Directories and projects are created only when their approved issue requires them.

## Local Development Topology

Issue #7 provides one Docker Compose development stack on the default Compose network:

```text
web (Next.js)  -> localhost:3000
api (FastAPI)  -> localhost:8000
db (PostgreSQL) -> localhost:5432
```

All host ports bind to loopback only. The containers support local development and do not make this codebase microservices: they are a convenient process boundary for the existing modular monolith. Production container topology remains unresolved.

## Main Components

### Telegram Browser Boundary

The Next.js root route renders Telegram controls only after `AuthProvider` establishes an authenticated
session. A focused browser API module uses credentialed `fetch` with the in-memory CSRF token for
state changes. A local React hook owns transient connection, deep-link, idempotency, polling, and
delivery-status state; it adds no client cache, persistent store, or frontend dependency.

### Web Application

The frontend uses Next.js with TypeScript, the App Router, and Tailwind CSS. Server Components are the default; client components are introduced only when browser state or effects are required. The initial authentication feature is a small client-side `AuthProvider` at the application root with in-memory safe user and CSRF values. Its feature-local API client uses native credentialed `fetch` against `NEXT_PUBLIC_API_BASE_URL`; it has no global state framework and never reads the HTTP-only cookie. Sign-in and sign-up routes use feature-local semantic forms, while the root route renders loading, unauthenticated, and authenticated states.

Responsibilities:

- Registration, sign-in, session restoration, and current-session sign-out UI.
- Telegram connection UI.
- Signal-template browsing.
- Custom alert builder.
- Active alert management.
- Alert and notification history.
- User-facing explanation of timeframe, evaluation mode, and cooldown.

The frontend must not be the authority for ownership, trigger state, or sensitive validation.

### API

The API uses Python `3.14`, FastAPI, and uv for Python installation, dependency management, command execution, and locking. `create_app()` in `apps/api/src/freecoinalert_api/main.py` provides the application-factory boundary, and `api/router.py` composes route modules so future features do not attach routes directly to the application entry point.

The API implements unauthenticated `GET /health`, which reports API process health only
and does not query PostgreSQL, plus `POST /auth/register`, `POST /auth/login`,
`GET /auth/me`, and `POST /auth/logout`. Authentication routes compose email
normalization, Argon2id password hashing, session creation, origin checks, a bounded
single-process rate limiter, and the reusable authenticated-principal and CSRF
dependencies around the asynchronous SQLAlchemy and Psycopg 3 persistence boundary for
`users` and `auth_sessions`. Pydantic Settings reads `DATABASE_URL`, `db/session.py`
provides one `AsyncSession` per request, repositories hold persistence operations, and
Alembic owns migrations. Session lookup uses only the HTTP-only cookie, fixed expiry,
and revocation state; it does not refresh a session during normal requests.

Issue #19 extends that persistence boundary with typed Telegram connection, link-token,
and processed-update models plus transactional repositories. Issue #20 adds a focused
Telegram API route, schemas, an application service, cryptographic link helper, and bounded
process-local limiter. The service owns token generation, SHA-256 hashing, replacement and
disconnect transactions, and safe state derivation; repositories remain transport-independent.
There is still no Telegram client, webhook, polling, `/start` parser, confirmation message, or
notification worker.

Responsibilities:

- Authentication and authorization.
- User and Telegram-connection resources.
- Signal-template and alert resources.
- Server-side validation of custom rules.
- Alert-history and delivery-status queries.
- Administrative management of supported markets and templates when introduced.

### Market-Data Process

Responsibilities:

- Shared Binance WebSocket connections.
- Real-time price events.
- One-minute kline ingestion.
- Closed-candle persistence.
- Reconnection and gap detection.
- UTC-aligned aggregation to larger timeframes.
- Daily reconciliation of missing candles.

Issue #48 adds the shared API-package persistence boundary for canonical and derived candle rows. It has no executable provider client or aggregation scheduler: Issue #49 will supply closed-kline ingestion, bootstrap, reconciliation, and runtime aggregation orchestration.
- Rate-limited historical backfill.

It must not create a connection per user or run expensive historical work on the real-time path.

The initial catalog is an API-owned persistence boundary rather than a process: it supports five allowlisted
Binance Spot USDT symbols and records only the metadata necessary for safe future price validation.

### Strategy Core

Responsibilities:

- Candle models and aggregation.
- Indicator calculations.
- Comparison and crossover conditions.
- Logical rule composition.
- Rule validation.
- Deterministic strategy evaluation.
- Strategy-template version models.

Live alert evaluation and future historical analysis must call the same strategy-core implementation.

Issue #51 begins this boundary in the API package with provider-neutral immutable candle inputs and pure Decimal
SMA 200 / Wilder RSI 14 functions. It has no database session, provider client, cache, subscription lookup,
crossing decision, or event persistence. Future coordinators may share results by market, timeframe, fixed
strategy parameters, and calculation version, while rebuilding from canonical candles after a revision.

### Alert Engine

Responsibilities:

- Load or index active alerts.
- Evaluate price alerts from real-time price events.
- Evaluate indicator alerts from closed candles.
- Maintain state needed for crossing and cooldown behavior.
- Share calculations between alerts where practical.
- Create reproducible alert events.
- Prevent duplicate trigger events.

### Notification Process

Responsibilities:

- Claim durable notification-outbox records.
- Send Telegram messages.
- Record delivery state and provider identifiers where useful.
- Retry temporary failures with bounded backoff.
- Mark permanent failures clearly.

Alert evaluation and Telegram delivery are separate outcomes.

### Database

Responsibilities:

- Product and user data.
- Telegram connections.
- Signal templates and versions.
- User alert definitions and evaluation state.
- Alert events and notification jobs.
- Canonical closed one-minute candles.
- Data-quality and reconciliation state.
- Future historical-analysis jobs and results.

PostgreSQL is the initial relational database direction. The API reaches the local
Compose database through `postgresql+psycopg://…@db:5432/…` after `db` is healthy;
direct-host API development uses `localhost`. Hosting remains undecided.

## Primary Data Flows

### Telegram Linking

```text
Authenticated user
    -> request one-time link token
    -> open Telegram bot deep link
    -> Telegram sends /start token
    -> backend validates token
    -> backend stores chat destination
    -> bot sends confirmation
```

### Immediate Price Alert

```text
Binance price event
    -> identify relevant alert groups
    -> evaluate threshold/crossing state
    -> create alert event and outbox record atomically
    -> notification process sends Telegram message
```

### Candle-Close Indicator Alert

```text
Binance 1m kline closes
    -> upsert canonical candle
    -> update required aggregate candles
    -> update shared indicators
    -> evaluate matching rules
    -> create alert event and outbox record atomically
    -> notification process sends Telegram message
```

### Reconciliation

```text
Scheduled job
    -> detect missing closed 1m timestamps
    -> fetch only missing Binance REST ranges
    -> respect rate limits and retry guidance
    -> upsert candles
    -> update gap status
```

### Future Historical Analysis

```text
User requests analysis
    -> validate strategy and date range
    -> confirm internal candle coverage
    -> run isolated historical job using strategy-core
    -> store assumptions, metrics, and result
```

## Scaling Principles

- Scale by unique market-data and calculation combinations, not by duplicating work per user.
- Share Binance streams by exchange, market, symbol, and stream type.
- Share indicator calculations by symbol, timeframe, indicator, and parameters.
- Keep historical jobs isolated from real-time ingestion.
- Introduce queues, caches, or service separation only after bottlenecks are measured.
- Preserve provider portability through environment configuration and containers.

## Reliability Boundaries

- WebSocket ingestion is primary for current data.
- REST reconciliation repairs missing history.
- Database writes must be idempotent.
- An alert event and its notification job must be created atomically.
- Notification retries must not create duplicate user-visible alerts.
- API process health is not equivalent to market-data freshness or notification health.

## Pending Architecture Decisions

## Issue #22 Notification Worker

The notification worker remains an executable in `apps/api`, sharing its configuration, Telegram
client boundary, and async database sessions. The authenticated API queues PostgreSQL outbox rows;
the separate worker claims and sends them without holding database locks during network calls.
The optional Compose `telegram` profile runs both update polling and notification delivery while
the default development stack needs no Telegram credentials.

- Feature-specific frontend architecture, including component boundaries and client-state needs.
- Authentication implementation and provider.
- Database hosting.
- Webhook versus long polling for Telegram during development and production.
- Initial approach for scheduling reconciliation and historical jobs.

## Issue #21 Telegram Processor

The local Telegram update processor is an executable inside `apps/api`, not a new service project.
It reuses the API package's settings, async database sessions, Telegram repositories, and linking
business service. Its typed Bot API client exposes only safe link-confirmation and failure messages.
Long polling is sequential and message-only; webhook deployment and durable notification delivery
remain separate boundaries.

## Issue #30 Alert API Boundary

The API now has a focused price-alert route, schemas, service, safe error boundary, and bounded local limiter.
The service coordinates authenticated ownership, catalog and Telegram readiness, idempotency, per-user creation
serialization, and commits; repositories remain persistence-focused. It does not own a Binance client, live-price
source, evaluator, alert event/outbox write, or Telegram delivery.
# Live-price stream boundary

The optional `market-stream` process reuses the API package, settings, SQLAlchemy models, catalog synchronization service, and database configuration. One WebSocket reader produces normalized `PriceEvent` values for an ordered internal queue; Issue #31 registers only the durable market-state recorder. Issue #32 may add an alert evaluator sink to the same pipeline. Provider-specific JSON and WebSocket handling remain in `market_data/binance_websocket.py`, outside alert-domain logic.

Issue #32 adds that evaluator as the ordered sink after market-state recording. It maintains a read-optimized
active registry but locks and revalidates candidates in PostgreSQL; a trigger atomically writes the immutable
event, terminal alert state, and Telegram outbox job. Telegram delivery remains a separate worker concern.

## Browser Price-Alert Boundary

Issue #33 adds focused catalog and alert browser modules to the existing Next.js root route. Native fetch,
React state/effects/refs, the established authentication provider, and the Telegram connection read boundary
remain the only client-side dependencies. The browser is a typed consumer of the API's safe catalog and alert
contracts; it does not own lifecycle evaluation, decimal persistence, authorization, or provider connectivity.
# Candle-data boundary

The existing singleton `market-stream` owns Binance Spot aggregate-trade and candle connectivity
under one advisory lock. It has a bounded confirmed-candle queue for operational state and safe
observability only. Future preset evaluation is a later sink; provider payloads do not enter strategy code.

Issue #52 makes preset evaluation that next sink: confirmed-candle persistence and aggregation feed one singleton evaluator, which persists global evaluation state and immutable market signal events. Browser feed delivery and Telegram notification creation remain separate future boundaries.
