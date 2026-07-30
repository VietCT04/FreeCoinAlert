# Concerns

This file records unresolved risks, assumptions, and decisions requiring human review.

Do not hide important uncertainty only in code comments or pull-request discussion. Add it here when it affects product behavior, security, reliability, data quality, cost, or future compatibility.

## Open Concerns

### C-025: One-Time Price Alert Evaluation and Delivery Remain Pending

**Status:** Partially resolved by GitHub Issue #29

Issue #29 stores exact price-alert definitions, snapshots, crossing state, lifecycle timestamps, and
immutable one-time trigger events. It deliberately provides no alert API, live Binance source,
evaluator, or transaction that creates an outbox job with an event.

**Why it matters:** The persistence boundary prevents a triggered alert from being reactivated and
provides deduplication data, but correct live crossing and atomic notification behavior require Issues
#30 through #32. No migration, database command, test, or verification command was run by maintainer
direction.

### C-026: Price Alert API Awaiting Live Evaluation

**Status:** Partially resolved by GitHub Issue #30

Issue #30 provides authenticated creation, owned read/list, and soft-delete behavior with exact decimal
validation, idempotency, catalog and Telegram checks, and bounded local limits. It intentionally does not fetch
the current price, connect to Binance, evaluate crossings, create alert events/outbox rows, or send Telegram.
No tests, migrations, application startup, HTTP requests, builds, linting, formatting, type checks, or other
verification commands were run by maintainer direction.

**Why it matters:** A created alert starts with no relation and cannot notify until a future centralized stream
and evaluator initialize it. Process-local rate limits must be replaced before multiple API replicas or public
launch.

### C-020: Authentication API and Single-Process Rate Limiting

**Status:** Partially resolved by GitHub Issues #13, #14, and #15

Registration and sign-in use normalized email identity, Argon2id password hashes, seven-day absolute session expiry, HTTP-only browser-session cookies, and a bounded in-process limiter. The limiter applies only within one API process and uses the direct client address; it is not appropriate for multiple replicas or an untrusted reverse-proxy deployment.

**Why it matters:** A public or horizontally scaled deployment requires a shared rate-limit store and an approved trusted-proxy design. Current-user, current-session logout, session revocation, and the minimal browser session flow are now implemented; account deletion and the production cookie/TLS deployment posture remain separate work. The authentication implementation has not received a dedicated verification pass.

### C-021: Telegram Production Transport and Shared Limiting Remain Open

**Status:** Partially resolved by GitHub Issue #21

Issues #19 and #20 provide the constrained connection, hashed link-token, and
processed-update persistence boundary plus authenticated APIs for one-time link creation,
safe connection state, and idempotent disconnect. Link tokens use a configurable ten-minute
local default, replacement and disconnect revoke outstanding tokens transactionally, and
bounded per-process limits cover link creation and disconnect.

**Why it matters:** Issue #21 implements local sequential long polling, atomic update processing,
and bounded cleanup, but production webhook transport, processor supervision, and shared
cross-replica rate limiting remain decisions. A public or multi-replica deployment needs a shared
limiter and approved trusted-proxy design before the local limits are sufficient.

### C-019: Authentication Persistence Foundation

**Status:** Resolved by GitHub Issue #11

The initial PostgreSQL persistence layer uses UUID user accounts with a unique normalized
email and revocable, expiring authentication sessions. Password and session tokens are
stored only as hashes; session deletion cascades when a user is deleted.

**Why it matters:** This establishes durable, minimal ownership data without deciding
registration behavior, email validation, session lifetimes, cookie attributes, account
deletion policy, or an authentication provider.

### C-018: Local Compose and PostgreSQL Development Foundation

**Status:** Resolved by GitHub Issue #7

The repository uses a local Docker Compose stack containing the web application, API, and PostgreSQL `18.4`, with Docker-managed persistent and dependency volumes.

**Why it matters:** This provides a predictable local startup path without selecting a production database provider, backup policy, deployment design, or production container topology.

### C-017: Backend Framework and Project Management Foundation

**Status:** Resolved by GitHub Issue #6

The first backend application uses Python `3.14`, FastAPI `0.139.2`, and uv. Ruff and mypy provide the configured formatting, linting, and static type-checking contracts.

**Why it matters:** This establishes a small, locked, Python API foundation without deciding database integration, authentication, CORS, deployment, workers, or external integrations.

### C-016: Frontend Framework Foundation

**Status:** Resolved by GitHub Issue #5

The browser application uses Next.js `16.2.9`, TypeScript, the App Router, Tailwind CSS, ESLint, and Server Components by default.

**Why it matters:** This provides a small, supported frontend base without deciding authentication, API integration, deployment, or a reusable UI system.

### C-015: Monorepo Workspace Foundation

**Status:** Resolved by GitHub Issue #4

The repository uses native pnpm workspaces with Node.js `24.18.0`, pnpm `11.4.0`, Prettier, and EditorConfig. Nx and Turborepo are intentionally not used.

**Why it matters:** This establishes a lightweight, portable repository-level workflow while leaving frontend, backend, Docker, deployment, and hosting choices to their own approved issues.

### C-001: Product Name and Domain

**Status:** Open

`FreeCoinAlert` is the current repository and working product name. The final public name, domain, trademark risk, and search-positioning strategy have not been decided.

**Why it matters:** Renaming later affects branding, package names, public URLs, Telegram bot identity, and documentation.

### C-002: Initial Binance Market

**Status:** Resolved for the initial catalog by Issue #28

The initial supported market is Binance Spot only. Futures, margin, options, and additional exchanges remain
out of scope until a later approved issue expands the catalog.

**Why it matters:** Stream names, symbol metadata, prices, candle semantics, user expectations, and future strategy assumptions differ by market.

### C-003: Supported Symbols

**Status:** Resolved for the initial catalog by Issue #28

The initial allowlist is `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `SOLUSDT`, and `XRPUSDT`. Product enablement is
code- and migration-controlled in this MVP; catalog expansion and an operator refresh policy remain future
work.

**Why it matters:** Symbol count drives WebSocket subscriptions, storage growth, reconciliation requests, and user value.

### C-004: Authentication Design

**Status:** Partially resolved by GitHub Issues #11, #13, #14, and #15

Issue #13 establishes email normalization, Argon2id password hashing, seven-day absolute
session expiry, browser-session cookie attributes, and local single-process authentication
rate limits. Issue #14 adds current-user lookup, current-session revocation, an
authenticated-principal ownership boundary, and CSRF enforcement for state changes.
Account deletion, trusted proxies, shared rate limiting, and production deployment
implications remain undecided. The frontend keeps safe user and CSRF state only in
memory and restores it through the current-user API; browser-flow verification remains
pending a maintainer-requested dedicated pass.

**Why it matters:** It affects the database, API, frontend, security, account deletion, and hosting cost.

### C-005: Telegram Destination Scope

**Status:** Open

The initial design assumes one private Telegram chat per user. Multiple destinations, groups, and channels are undecided.

**Why it matters:** Group ownership, bot permissions, disconnect behavior, and destination authorization are more complex.

### C-006: Alert Cooldown Semantics

**Status:** Open

It is undecided whether cooldown begins when an alert event is created or after successful notification delivery, and whether suppressed events are stored.

**Why it matters:** Users may interpret alert history and delivery frequency differently.

### C-007: Custom Alert Editing

**Status:** Open

It is undecided whether editing an active custom alert mutates the existing definition, creates an immutable version, or creates a replacement alert.

**Why it matters:** Evaluation state, crossover behavior, audit history, and reproducibility depend on this decision.

### C-008: Indicator Library and Numeric Consistency

**Status:** Open

No indicator library or numeric precision approach has been selected.

**Why it matters:** Live incremental calculations and historical batch calculations must match exactly enough to avoid inconsistent trigger times.

### C-009: Candle Retention and Partitioning

**Status:** Open

The one-minute candle retention period, supported history, and partitioning strategy are undecided.

**Why it matters:** Data volume can grow into tens of millions of rows and affects cost, backups, queries, and future analysis.

### C-010: Missing Candle Behavior

**Status:** Open

The current principle is to mark aggregates incomplete and avoid evaluating them. Exact user-facing behavior and retry thresholds are undecided.

**Why it matters:** Silent evaluation from incomplete data could create incorrect alerts.

### C-011: Hosting and Database Provider

**Status:** Open

The MVP will be built provider-independently. Managed hosting versus a VPS and managed versus self-hosted PostgreSQL remain undecided.

**Why it matters:** Cost, reliability, backups, deployment, maintenance, and regional latency differ.

### C-012: Free Product Limits and Monetization

**Status:** Open

The app is intended to launch free, but active-alert limits, historical-analysis limits, ads, affiliate links, and paid plans are not decided.

**Why it matters:** Usage limits affect architecture and user expectations, while monetization can introduce compliance and trust considerations.

### C-013: Historical Performance Communication

**Status:** Open

The product must define how it labels simulated performance and what disclaimers and assumptions are mandatory.

**Why it matters:** Win rate without execution, fees, slippage, sample size, and date range can mislead users.

### C-014: Data and Account Deletion

**Status:** Open

Deletion and retention behavior for account data, Telegram identity data, alerts, events, deliveries, audit logs, and historical results is undecided.

**Why it matters:** Security, privacy, support, reproducibility, and storage requirements are affected.

## Concern Workflow

### C-024: Catalog Synchronization Verification and Scheduling

**Status:** Open

Issue #28 adds an explicit public Binance metadata synchronization command but does not contact Binance,
run the command, apply its migration, or exercise the read endpoint during implementation. The refresh
scheduler, production rate-limit observations, and operator ownership are intentionally unresolved.

**Why it matters:** Safe availability depends on current provider metadata, while automatic scheduling must
be designed to avoid uncoordinated provider traffic and preserve the last valid catalog on failure.

### C-023: Telegram Browser and Provider Verification

**Status:** Open

Issue #23 implements the browser connection, test-notification, and disconnect flow without opening a
Telegram deep link, contacting the Bot API, or running browser/API verification. The UI can report only
the API's safe outbox status and cannot prove delivery to a user's device.

**Why it matters:** A maintainer-directed pass with a configured bot is needed to validate popup fallback,
link completion, polling behavior, provider acceptance, and safe degraded/delivery-error presentation.

### C-022: Notification Worker Delivery Boundaries

Issue #22 introduces a PostgreSQL test-notification outbox and a process-local request limiter.
The worker intentionally fails uncertain network outcomes and stale claims rather than retrying
without a Telegram application idempotency key. Multi-replica API rate limiting, production worker
supervision, alert-triggered delivery, and operational retention policy remain future decisions.

When adding a concern:

1. Assign the next stable identifier.
2. Explain the uncertainty and why it matters.
3. Link the deciding GitHub Issue when created.
4. Update the status when resolved.
5. Update the source-of-truth document with the approved decision.
6. Keep resolved concerns when historical context remains useful, or archive them through an approved documentation change.
