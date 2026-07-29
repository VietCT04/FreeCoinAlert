# Concerns

This file records unresolved risks, assumptions, and decisions requiring human review.

Do not hide important uncertainty only in code comments or pull-request discussion. Add it here when it affects product behavior, security, reliability, data quality, cost, or future compatibility.

## Open Concerns

### C-020: Authentication API and Single-Process Rate Limiting

**Status:** Partially resolved by GitHub Issues #13 and #14

Registration and sign-in use normalized email identity, Argon2id password hashes, seven-day absolute session expiry, HTTP-only browser-session cookies, and a bounded in-process limiter. The limiter applies only within one API process and uses the direct client address; it is not appropriate for multiple replicas or an untrusted reverse-proxy deployment.

**Why it matters:** A public or horizontally scaled deployment requires a shared rate-limit store and an approved trusted-proxy design. Current-user, current-session logout, and session revocation are now implemented; account deletion and the production cookie/TLS deployment posture remain separate work.

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

**Status:** Open

The first supported market has not been finalized. The MVP may start with Binance Spot only or include USD-M Futures.

**Why it matters:** Stream names, symbol metadata, prices, candle semantics, user expectations, and future strategy assumptions differ by market.

### C-003: Supported Symbols

**Status:** Open

The initial symbol list and process for adding or removing symbols are undecided.

**Why it matters:** Symbol count drives WebSocket subscriptions, storage growth, reconciliation requests, and user value.

### C-004: Authentication Design

**Status:** Partially resolved by GitHub Issues #11, #13, and #14

Issue #13 establishes email normalization, Argon2id password hashing, seven-day absolute
session expiry, browser-session cookie attributes, and local single-process authentication
rate limits. Issue #14 adds current-user lookup, current-session revocation, an
authenticated-principal ownership boundary, and CSRF enforcement for state changes.
Account deletion, trusted proxies, shared rate limiting, and production deployment
implications remain undecided.

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

When adding a concern:

1. Assign the next stable identifier.
2. Explain the uncertainty and why it matters.
3. Link the deciding GitHub Issue when created.
4. Update the status when resolved.
5. Update the source-of-truth document with the approved decision.
6. Keep resolved concerns when historical context remains useful, or archive them through an approved documentation change.
