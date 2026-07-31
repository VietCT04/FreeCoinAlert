# Security

## Purpose and Security Scope

This document records implemented security boundaries and limitations for the alert-only product. It does not claim a security review or runtime verification.

## Assets and Trust Boundaries

Sensitive assets are password hashes, session and CSRF tokens, Telegram bot credentials and destinations, database credentials, and user-owned records. The browser is untrusted. Binance is a public market-data provider; Telegram is an external delivery provider. PostgreSQL is the durable trust boundary.

## Authentication and Session Security

Passwords are validated at 15–128 characters and stored using pwdlib’s recommended Argon2id policy. Sessions use `secrets.token_urlsafe(32)` tokens; only SHA-256 token hashes are stored. A session has a random CSRF token, expiry from `SESSION_TTL_SECONDS` (default seven days), and revocation timestamp. The `freecoinalert_session` cookie is HTTP-only, `SameSite=Lax`, path `/`, and conditionally Secure. Sign-out revokes a live session and clears the cookie.

## CSRF, CORS, Origin, and Browser Storage

Authenticated mutations compare `X-CSRF-Token` with the session token using constant-time comparison. Registration/login accept only `WEB_ORIGIN` or the API origin when `Origin` is present. CORS is one configured origin with credentials and a narrow method/header list. The web client keeps authentication and CSRF values in memory; no sensitive session or linking token is intentionally persisted in browser storage.

## Authorization and Ownership

The server derives the principal from the session. Alert, subscription, Telegram, and notification repositories use that ID for ownership checks. Client-supplied user identifiers do not select resources. API responses are shaped to avoid exposing another user’s resource details.

## Input Validation and Abuse Controls

Pydantic forbids unknown fields in security-sensitive request bodies; UUIDs, exact decimals, catalogue availability, and lifecycle transitions are validated server-side. Authentication, alert, signal, and Telegram actions use bounded 15-minute in-memory rate-limit buckets. These controls are process-local, not distributed abuse protection.

## Telegram Security

The bot token is environment configuration and is never returned by HTTP APIs. Link values are random, short-lived, single-use values stored as hashes. Processed Telegram update IDs are persisted for idempotency. Connections retain only the provider identity and delivery fields required for the feature. Provider errors are normalized before user-facing responses and logs must not contain bot tokens or raw link values.

## Binance and Market-Data Security

Binance Spot REST/WebSocket access is public and centralized. The product neither requests nor stores customer exchange API keys. Provider input is normalized and freshness/order/data-quality guarded before it changes alert or candle state.

## Database and Secret Handling

`DATABASE_URL`, Telegram bot token, and local passwords are environment configuration. Tokens are hashed where replay is not needed; passwords are Argon2id hashes. Exact decimal values use `NUMERIC`, avoiding float-based financial persistence. Database deletion/backup policy remains an operational concern documented in [DATABASE.md](DATABASE.md).

## Logging and Error Redaction

Structured logs may contain lifecycle identifiers and safe failure codes. They must not include passwords, session or CSRF tokens, Telegram bot/link tokens, database URLs, raw provider payloads, or unnecessary personal data. API errors return stable safe codes/messages rather than internal exceptions.

## Frontend Information Exposure

The frontend receives only response DTOs for its authenticated principal and public catalogue/preset data. It does not receive password hashes, session hashes, internal signal calculation state, provider secrets, or other users’ data.

## Current Limitations and Unresolved Risks

Rate limits are process-local. There is no documented production backup, account-deletion, distributed rate-limit, security-review, penetration-test, or provider-verification outcome. Runtime CORS/cookie deployment values require an explicit operational review before exposure beyond the configured origin.

## Verification Status

Security behavior was inspected statically from code and configuration. No penetration test, provider request, browser flow, migration, or runtime security verification was run.
