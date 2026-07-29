# Security

## Purpose

This document defines the initial security boundaries and minimum controls for authentication, authorization, Telegram linking, custom strategy rules, external integrations, secrets, abuse prevention, and logging.

## Security Principles

- Treat all client input and external-provider input as untrusted.
- Enforce ownership and permissions server-side.
- Store the minimum sensitive data required.
- Never commit secrets.
- Use constrained rule definitions instead of executing customer code.
- Make sensitive external-event processing idempotent.
- Prefer deny-by-default behavior for unsupported markets, symbols, indicators, operators, and parameters.

## Authentication

Issue #11 establishes persistence only. `users` stores a password hash, never a raw
password, and enforces unique `email_normalized` identity. `auth_sessions` stores only
a unique session-token hash, explicit expiry, and optional revocation time. It permits
multiple concurrent sessions per user and cascades their deletion when the owning user
is deleted. The CSRF token may be stored directly because it cannot authenticate a user
without the HTTP-only session cookie.

Registration and sign-in normalize email identity, use Argon2id password hashes, and
establish a seven-day fixed-expiry browser session. `GET /auth/me` resolves the session
only from the HTTP-only `freecoinalert_session` cookie. It maps a SHA-256 token hash to
one unrevoked, unexpired session and its owning user, without extending expiry or writing
last-seen state. Missing, malformed, invalid, expired, and revoked cookies are rejected
consistently and may be cleared.

The immutable `AuthenticatedPrincipal` is the reusable ownership boundary. It contains
only the authenticated user UUID and session UUID. Future user-owned endpoints must
derive ownership from that principal and never treat a client-supplied user ID as proof.

The browser authentication flow uses credentialed `fetch` requests to the configured API
origin. It keeps only the safe current user and session-bound CSRF token in React memory;
it never reads the HTTP-only session cookie or writes authentication data to browser
persistent storage, query parameters, or frontend-created cookies. A refresh restores
that memory state only through `GET /auth/me`.

Cookie-authenticated POST, PUT, PATCH, and DELETE endpoints must use the reusable CSRF
dependency. It accepts `X-CSRF-Token` only as a header and compares it in constant time
to the session-bound CSRF token. Logout revokes only the current session after a valid
CSRF check, clears the cookie, and is intentionally idempotent for absent, invalid,
expired, or revoked sessions. Concurrent sessions remain allowed; expiry is absolute and
sessions are not rotated or extended on ordinary requests.

The implemented approach provides:

- Secure password or identity-provider handling.
- Session expiration and revocation.
- CSRF protection when cookie-based sessions are used.
- Secure cookie settings where applicable.
- Rate limiting for sign-up and sign-in attempts.
- A reliable current-user identity for authorization decisions.

The backend must derive the user from the authenticated principal. A client-provided user identifier is never proof of identity or ownership.

## Authorization

Users may access only their own:

- Alert definitions
- Telegram connections
- Alert events
- Notification settings and delivery records
- Future historical-analysis jobs and results

Administrative endpoints, when introduced, require explicit admin authorization.

Internal worker operations must not be exposed as unauthenticated public endpoints.

## Telegram Linking

The web application must not ask users to type a Telegram chat ID manually.

The recommended flow uses a short-lived, single-use deep-link token.

Required controls:

- Generate tokens with cryptographically secure randomness.
- Bind each token to the authenticated requesting user.
- Expire tokens within a short documented period.
- Invalidate tokens after successful use.
- Prevent replay.
- Do not encode raw internal user IDs in the token.
- Store a token hash where practical.
- Process Telegram updates idempotently.
- Validate webhook authenticity using Telegram's supported secret mechanism when webhooks are used.

## Telegram Data

Store only data needed to deliver and manage alerts, such as:

- Telegram chat ID
- Connection state
- Telegram username when product requirements justify it
- Connection and verification timestamps

Do not expose chat IDs unnecessarily in the frontend or logs.

## Customer Strategy Rules

Customers must not be allowed to submit executable Python, JavaScript, SQL, shell commands, templates with arbitrary execution, or uploaded plugins.

Custom rules must use a validated internal format.

Validation must restrict:

- Supported indicators
- Supported operators
- Parameter ranges
- Timeframes
- Rule depth
- Number of conditions
- Calculation complexity
- Supported symbols and markets

The backend is authoritative even when the frontend performs the same validation for user experience.

## Exchange Credentials

The alert-only MVP must not request or store customer Binance API keys.

The platform should consume public market data only.

Any future trading integration requires a separate security design and explicit product approval.

## Secret Management

Secrets include:

- Authentication secrets
- Database credentials
- Telegram bot token
- Telegram webhook secret
- External monitoring tokens
- Encryption keys

Rules:

- Use environment variables or an approved secret manager.
- Provide `.env.example` with names only, never real values.
- Rotate a secret immediately if it is exposed.
- Avoid printing secrets in logs or error responses.
- Keep production secrets separate from local and test environments.

## Abuse Prevention

Rate-limit operations that can create cost or spam:

- Authentication attempts
- Telegram-link token creation
- Test notifications
- Alert creation and modification
- Historical-analysis submission
- Public endpoints vulnerable to scraping or enumeration

Introduce per-user alert and rule-complexity limits before public launch.

## Input Validation

Validate:

- Symbol, exchange, market, and timeframe
- Decimal values and reasonable thresholds
- Indicator periods and parameters
- Cooldown ranges
- Rule structure and schema version
- Date ranges for historical analysis
- Pagination and sorting values

Do not pass user-provided identifiers directly into SQL, shell commands, file paths, or external URLs.

## Logging and Error Handling

- Use structured logs.
- Do not log passwords, sessions, tokens, secrets, or full sensitive provider payloads.
- Avoid logging every market tick.
- Return safe error messages and stable error codes.
- Correlate errors with a request or event identifier.
- Preserve enough audit information for sensitive account and alert changes.

## Dependency and Container Security

- Pin and update dependencies intentionally.
- Review high-severity vulnerabilities.
- Run application containers as non-root when practical.
- Keep runtime images minimal.
- Do not expose database or worker ports publicly unless required.
- Apply security updates to any VPS or host operating system.

## Security Review Triggers

Update this document and request review when introducing:

- Exchange API keys or trade execution
- Payments or paid plans
- Additional notification providers
- File uploads
- Public sharing of strategies
- Arbitrary formulas or scripting
- Administrative dashboards
- Multi-tenant organizations
- New personal data

## Pending Decisions

- Authentication provider.
- Encryption requirements for Telegram destination identifiers.
- Initial rate-limit thresholds.
- Account deletion and data-retention behavior.
- Audit-log schema and retention.
- Production secret-management provider.
