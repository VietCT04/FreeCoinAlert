# API

## Purpose

This document defines API-wide conventions and the planned resource areas. Exact endpoint contracts must be added by the GitHub Issue that implements them.

## Status

The API implements the unauthenticated process-health endpoint, browser-session authentication,
and authenticated Telegram link-token, connection-state, and disconnect endpoints.

Do not treat the examples below as final contracts. They define naming and behavior expectations for future implementation.

## Implemented Endpoints

### API Process Health

`GET /health`

Requires no authentication and returns HTTP `200` when the API process is running.

Response:

```json
{
  "status": "ok",
  "service": "freecoinalert-api"
}
```

This is liveness/process health only. It performs no database or external-network calls and does not represent readiness for PostgreSQL, market-data ingestion, alert evaluation, Telegram delivery, or future workers. Standard FastAPI OpenAPI endpoints remain available at `/docs`, `/redoc`, and `/openapi.json`.

### Account Registration and Sign-In

`POST /auth/register` creates an account and returns HTTP `201`. `POST /auth/login` verifies an existing account and returns HTTP `200`. Both accept JSON with `email` and `password`, and return:

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "createdAt": "UTC timestamp"
  },
  "csrfToken": "random CSRF token"
}
```

Successful responses set the `freecoinalert_session` cookie with `HttpOnly`, `SameSite=Lax`, `Path=/`, no `Domain`, and no `Expires` or `Max-Age`. `SESSION_COOKIE_SECURE` controls its `Secure` attribute; it is false only for local HTTP development. The raw session token is never returned in JSON, readable response headers, URLs, or browser storage. Successful responses include `Cache-Control: no-store`.

Email input is trimmed, validated without DNS or deliverability checks, normalized by `email-validator`, and case-folded for the database identity lookup. Passwords are not trimmed; they accept Unicode and spaces and must contain 15 through 128 Unicode code points. New hashes use Argon2id.

Authentication errors use `{ "code", "message", "details": [] }`. `AUTH_REGISTRATION_UNAVAILABLE` safely covers duplicate registration, `AUTH_INVALID_CREDENTIALS` covers both missing accounts and incorrect passwords, `AUTH_REQUEST_INVALID` covers malformed or invalid input, `AUTH_ORIGIN_REJECTED` covers an explicit unapproved browser origin, and `AUTH_RATE_LIMITED` returns HTTP `429` with `Retry-After`.

The API accepts the configured `WEB_ORIGIN` with credentialed CORS and accepts its own origin for local Swagger requests. It rejects an explicitly supplied unapproved `Origin`. Registration is limited to five attempts per IP per 15 minutes; login is limited to ten attempts per IP, with five failed attempts per normalized-email-and-IP pair, in the same window. CORS permits `GET` and `POST` with `Content-Type` and `X-CSRF-Token` headers.

### Current User and Logout

`GET /auth/me` validates only the `freecoinalert_session` cookie and returns HTTP `200` with the same safe user object and session-bound `csrfToken` returned by registration and sign-in. It always returns `Cache-Control: no-store`. Missing, malformed, unknown, expired, or revoked cookies return HTTP `401` with `AUTHENTICATION_REQUIRED`; stale cookies are cleared when that response can be produced.

`POST /auth/logout` accepts `X-CSRF-Token` only as a request header. For a valid active session, the API compares it to the session-bound CSRF token in constant time, revokes only that session, clears the cookie, and returns HTTP `204` with `Cache-Control: no-store`. Missing, expired, revoked, malformed, or unknown session cookies also clear the cookie and return `204` without revealing whether a session existed. A valid active session with a missing or invalid CSRF header returns HTTP `403` with `AUTH_CSRF_INVALID` and does not revoke the session.

All cookie-authenticated endpoints derive identity through the immutable server-side `AuthenticatedPrincipal` containing only the user and session UUIDs. Future state-changing cookie-authenticated endpoints must reuse the CSRF dependency; they must not accept user IDs, session tokens, or CSRF tokens through bodies, query strings, or authorization headers.

### Browser Authentication Client

The Next.js browser client uses `NEXT_PUBLIC_API_BASE_URL` and native `fetch` for each authentication request. It sends `credentials: "include"`, uses JSON content types for registration and sign-in, and parses the stable authentication error shape without displaying raw server payloads. The HTTP-only `freecoinalert_session` cookie is never read or stored by frontend code.

`GET /auth/me` restores the safe user and CSRF token into React memory after a page load. A `401` is a normal unauthenticated state; network and unexpected server failures show a retryable safe message. Registration and sign-in keep the safe user and CSRF token only in memory, while sign-out sends the memory-only token as `X-CSRF-Token`. No authentication value is placed in localStorage, sessionStorage, IndexedDB, URLs, or frontend-created persistent cookies.

### Telegram Connection

All Telegram connection responses use `Cache-Control: no-store`, derive ownership only from
the authenticated principal, and never expose Telegram user IDs, chat IDs, database IDs,
token hashes, or a previously issued raw link token.

`POST /telegram/link-tokens` requires the browser session and `X-CSRF-Token`, accepts no
request body, and returns `201`:

```json
{
  "connection": {
    "status": "linking",
    "linkExpiresAt": "UTC timestamp"
  },
  "telegramUrl": "https://t.me/<bot_username>?start=<one-time-token>"
}
```

The raw 43-character URL-safe token appears only in that response URL. The API generates 32
random bytes, stores only its SHA-256 hash, uses `TELEGRAM_LINK_TTL_SECONDS` (600 seconds
locally), revokes every outstanding unconsumed token for that user in the same transaction,
and commits before returning. `TELEGRAM_BOT_USERNAME` is optional at startup; when absent,
link creation returns `503 TELEGRAM_NOT_CONFIGURED`. Connected or degraded destinations return
`409 TELEGRAM_ALREADY_CONNECTED` until they are disconnected. Concurrent creation conflicts
return `503 TELEGRAM_LINK_UNAVAILABLE` without SQL details.

`GET /telegram/connection` requires the browser session but not CSRF and returns `200`:

```json
{
  "connection": {
    "status": "not_connected | linking | connected | degraded | disconnected",
    "username": "optional Telegram username",
    "connectedAt": "optional UTC timestamp",
    "lastVerifiedAt": "optional UTC timestamp",
    "linkExpiresAt": "optional UTC timestamp",
    "statusReason": "optional stable safe category"
  }
}
```

`linking` represents an active unexpired token, not a completed Telegram connection. A
disconnected row with a new active token also reports `linking`; no previous deep link can be
returned because its raw token is not stored.

`DELETE /telegram/connection` requires the browser session and `X-CSRF-Token`, accepts no
request body, and returns `204`. It locks and marks a current connection as `disconnected`,
clears degraded state, records `user_disconnected`, revokes outstanding unconsumed tokens, and
commits as one transaction. It is idempotent for missing or already disconnected connections;
the persistent row and Telegram identifiers are never released for reassignment. Temporary
persistence failure returns `503 TELEGRAM_CONNECTION_UNAVAILABLE`.

Link creation is limited to five requests per 15 minutes per authenticated user and ten per
15 minutes per direct client IP. Disconnect is limited to ten requests per 15 minutes per
authenticated user. The bounded application-local limiter returns `429
TELEGRAM_LINK_RATE_LIMITED` with `Retry-After`; it uses `request.client.host` and does not
trust `X-Forwarded-For`.

## General Conventions

### Telegram Test Notifications

`POST /telegram/test-notifications` requires the browser session, `X-CSRF-Token`, and an
`Idempotency-Key` UUID header; it accepts no body and returns `202` with a safe queued
notification. It queues work only for the authenticated user's connected destination. Replaying
the same accepted key returns the existing safe notification without another message or rate-limit
slot. New requests are limited to three per authenticated user per 15 minutes and return `429
TELEGRAM_TEST_RATE_LIMITED` with `Retry-After`.

`GET /telegram/test-notifications/{notification_id}` requires authentication and loads by both
user and notification ID. It maps internal queue states to `queued`, `sending`, `retrying`,
`sent`, or `failed`; a foreign ID is indistinguishable from a missing ID. Both endpoints use
`Cache-Control: no-store` and never expose provider, lock, connection, or chat details.

- Use JSON request and response bodies unless a documented endpoint requires another format.
- Use HTTPS outside local development.
- Authenticate server-side and derive the acting user from the authenticated principal.
- Never accept a client-provided `userId` as proof of ownership.
- Validate every request using shared schemas.
- Return stable machine-readable error codes with safe user-facing messages.
- Use UTC ISO 8601 timestamps in API contracts.
- Use explicit pagination for collection endpoints.
- Make retryable create operations idempotent where duplicate processing has meaningful effects.
- Do not expose provider secrets, raw stack traces, or another user's data.

## Planned Resource Groups

### Authentication and Current User

Implemented responsibilities:

- Account registration and sign-in with browser-session establishment.
- Current-user retrieval and current-session logout.
- Session validation and reusable authenticated-principal and CSRF boundaries.

Remaining responsibilities:

- Account-level preferences such as display timezone.

### Telegram Connections

Implemented responsibilities:

- Create a short-lived Telegram linking token.
- Read the current user's Telegram connection state.
- Disconnect a destination.

Remaining responsibility:

- Send a test notification.

Sensitive linking tokens must not be returned after use or stored in plaintext when avoidable.

### Supported Markets

Expected responsibilities:

- List supported exchanges, market types, symbols, timeframes, indicators, operators, and parameter constraints.
- Expose only combinations the backend can actually evaluate.

### Signal Templates

Expected responsibilities:

- List active platform-provided templates.
- Read a template version and its user-facing explanation.
- Subscribe to a specific version.

### User Alerts

Expected responsibilities:

- Create a template subscription or custom alert.
- List alerts owned by the current user.
- Read, update, pause, resume, and delete an owned alert.
- Validate rule definitions and usage limits server-side.

### Alert Events and Deliveries

Expected responsibilities:

- List triggered events for the current user's alerts.
- Show whether notification delivery is pending, sent, retrying, or failed.
- Never expose another user's destination details.

### Future Historical Analysis

Expected responsibilities:

- Submit an analysis job after validating strategy, date range, and data coverage.
- Read job state and results.
- Include assumptions, strategy version, sample size, fees, slippage, and date range.

Historical endpoints are out of scope for the alert-only MVP.

## Error Shape Direction

A future standard error response should contain fields equivalent to:

```json
{
  "code": "ALERT_RULE_INVALID",
  "message": "The alert rule contains an unsupported condition.",
  "details": [
    {
      "field": "trigger.conditions[0].operator",
      "reason": "UNSUPPORTED_VALUE"
    }
  ],
  "requestId": "..."
}
```

Do not include secrets, provider payloads, SQL details, or stack traces.

## Authorization Rules

- Users may access only their own alerts, Telegram connections, event history, and delivery records.
- Platform-template administration requires explicit admin authorization when introduced.
- Internal market-data and notification-worker actions must not be exposed as unrestricted public endpoints.
- Test-notification and alert-creation endpoints require rate limiting.

## Contract Change Rules

When an endpoint is added or changed:

1. Update shared DTOs and validation schemas.
2. Update backend behavior.
3. Update all frontend consumers.
4. Add or update authorization and validation tests where practical.
5. Update this document with the exact method, path, request, response, errors, and ownership rules.
6. Record incompatible changes explicitly rather than silently changing response shapes.

## Pending Decisions

- API versioning strategy.
- Pagination format.
- Standard error-code registry.
- Whether public market metadata is served through the API or generated into the frontend build.
