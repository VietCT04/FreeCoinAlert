# Security

## Purpose and Security Scope

This document records implemented security boundaries and limitations for the alert-only product. It does not claim a security review or runtime verification.

## Assets and Trust Boundaries

Sensitive assets are password hashes, session and CSRF tokens, Telegram bot credentials and destinations, database credentials, and user-owned records. The browser is untrusted. Binance is a public market-data provider; Telegram is an external delivery provider. PostgreSQL is the durable trust boundary.

## Authentication and Session Security

Passwords are validated at 15–128 characters and stored using pwdlib’s recommended Argon2id policy. Sessions use `secrets.token_urlsafe(32)` tokens; only SHA-256 token hashes are stored. A session has a random CSRF token, expiry from `SESSION_TTL_SECONDS` (default seven days), and revocation timestamp. The `freecoinalert_session` cookie is HTTP-only, `SameSite=Lax`, path `/`, and conditionally Secure. Sign-out revokes a live session and clears the cookie.

## CSRF, CORS, Origin, and Browser Storage

Authenticated mutations compare `X-CSRF-Token` with the session token using constant-time comparison. Registration/login accept only `WEB_ORIGIN` or the API origin when `Origin` is present. CORS is one configured origin with credentials and a narrow method/header list that includes `PUT` for the signal Telegram-delivery preference. The web client keeps authentication and CSRF values in memory; no sensitive session or linking token is intentionally persisted in browser storage. Telegram-delivery preference and readiness are server-owned response state and are not stored in `localStorage`.

The shared theme provider may persist only the light/dark/system UI preference under `freecoinalert.theme`; this value is non-sensitive and is not used for authentication, ownership, delivery, alert, signal, analysis, cursor, or provider state.

The signal UI persists only the literal `true`/`false` sound preference under `freecoinalert.signalSound.enabled.v1`; it never persists events, cursors, IDs, authentication, or Telegram data. Credentialed `EventSource` carries only the safe live-feed snapshots and control events.

## Authorization and Ownership

The server derives the principal from the session. Alert, subscription, Telegram, and notification repositories use that ID for ownership checks. Client-supplied user identifiers do not select resources. The Telegram-delivery preference endpoint locks and updates only a subscription owned by the authenticated principal. API responses are shaped to avoid exposing another user’s resource details.

## Historical Analysis Runs

Historical-analysis routes require an authenticated session; create and cancellation also require the existing CSRF token. The server derives `user_id` from that session, applies owner filtering to list/detail/cancel operations, serializes create attempts with the existing per-user advisory-lock pattern, and enforces the maximum of two queued or running runs per owner. A UUID `Idempotency-Key` is unique within the owner scope, and a replay with a different request identity is rejected without exposing another run.

Run snapshots contain only controlled market/preset/version/range metadata and safe lifecycle fields. The response omits user IDs, lock IDs, raw errors, candle IDs, provider payloads, credentials, and report bodies. The separate worker reads only server-owned run/dataset/snapshot rows, never accepts user formulas or assumptions, and publishes reports only for the claimed owner-scoped run. Report/trade/equity reads first authorize the run through the authenticated session and return no user ID, provider payload, raw exception, or mutable live state. Run creation performs configuration and range checks only; it does not call Binance, calculate indicators, simulate trades, or create signal/alert/delivery work.

The pure fixed-preset simulation engine accepts only the server-controlled versions, preset definitions, calculation versions, validated immutable dataset snapshots, and `fixed_horizon_v1` assumptions. It has no database, HTTP, worker, file, browser, environment, or provider access and does not accept user-authored formulas or parameters. Its result carries fixed safety disclosures, including that it is not financial advice or a prediction and that synthetic short results are not executable Binance Spot trades. The engine result contains no credentials, user identifiers, provider payloads, or delivery state.

## Input Validation and Abuse Controls

Pydantic forbids unknown fields in security-sensitive request bodies; UUIDs, exact decimals, catalogue availability, and lifecycle transitions are validated server-side. Authentication, alert, signal, Telegram, and historical-analysis actions use bounded 15-minute in-memory rate-limit buckets. Historical-analysis creates are limited to 10 per user and 30 per direct client IP, cancellations to 30 per user, and configuration/list/detail/report/trade/equity reads to 120 per user. Signal Telegram-delivery preference mutations are limited to 30 per user per 15 minutes. These controls are process-local, not distributed abuse protection.

## Telegram Security

The bot token is environment configuration and is never returned by HTTP APIs. Link values are random, short-lived, single-use values stored as hashes. Processed Telegram update IDs are persisted for idempotency. Connections retain only the provider identity and delivery fields required for the feature. Provider errors are normalized before user-facing responses and logs must not contain bot tokens or raw link values.

## Signal Feed Security

The historical feed and SSE stream require the existing opaque session cookie and configured credentialed CORS origin. They are read-only and do not require CSRF. The stream revalidates the session ID at most every 60 seconds and closes with `auth_expired` after revocation or expiry. `Last-Event-ID` and `after` are non-negative bounded cursors; they never select a user or resource.

History visibility joins signal events to the authenticated user's active or disabled subscription rows. Live and replay fan-out use active subscriptions only. Feed payloads expose immutable market/preset/candle/value snapshots as exact decimal strings, fixed invalidation messages, and no internal UUIDs, subscription/user identifiers, calculation state, provider payloads, Telegram status, or recommendation text. The durable `NOTIFY` payload contains only a stream sequence.

Feed history, stream-attempt, per-user connection, per-process connection, and per-connection queue limits are bounded in memory. These controls are process-local until shared infrastructure is approved. A full queue resets and closes the affected stream so missed records are recovered through the historical endpoint rather than silently dropped. Signal Telegram-delivery state history contains only owner-scoped subscription, market, preset, lifecycle, preference, and timestamps; it contains no Telegram identifiers or provider payloads.

The signal dispatcher evaluates occurrence-time state and current connection timing from server-owned rows; it never trusts client-supplied recipients or contacts Telegram. Preset-signal outbox payloads contain immutable market, preset, calculation, candle, occurrence, event, and subscription snapshots, but no user IDs, Telegram IDs, chat IDs, tokens, provider responses, or mutable preset data. The notification worker strictly validates that payload schema before provider contact and rechecks outbox references, subscription ownership/status/preference, event invalidation, and the current owned connected destination. Dispatcher and worker logs use notification/signal identifiers and safe counts/categories without recipient identifiers, message contents, or raw provider responses.

## Binance and Market-Data Security

Binance Spot REST/WebSocket access is public and centralized. The product neither requests nor stores customer exchange API keys. Provider input is normalized and freshness/order/data-quality guarded before it changes alert or candle state.

## Database and Secret Handling

`DATABASE_URL`, Telegram bot token, and local passwords are environment configuration. Tokens are hashed where replay is not needed; passwords are Argon2id hashes. Exact decimal values use `NUMERIC`, avoiding float-based financial persistence. Database deletion/backup policy remains an operational concern documented in [DATABASE.md](DATABASE.md).

The tracked root `.env.example` contains only safe local placeholders, and `.env` is ignored. `pnpm dev:setup` copies the example only when `.env` is absent and never overwrites an existing file. The setup/preflight parser reads names and values only to validate them, does not expand or execute file content, allows process-environment overrides, uses argument arrays with `shell: false` for Docker checks, and emits only variable names and corrective actions. It never prints secret values, passes secrets as command-line arguments, writes Telegram settings to `NEXT_PUBLIC_*`, or contacts a provider. Telegram is disabled by default; enabling it requires the accepted username format and a non-empty bot token.

## Logging and Error Redaction

Structured logs may contain lifecycle identifiers and safe failure codes. They must not include passwords, session or CSRF tokens, Telegram bot/link tokens, database URLs, raw provider payloads, or unnecessary personal data. API errors return stable safe codes/messages rather than internal exceptions.

## Frontend Information Exposure

The frontend receives only response DTOs for its authenticated principal and public catalogue/preset data. It does not receive password hashes, session hashes, internal signal calculation state, provider secrets, Telegram destination identifiers, raw provider payloads, or other users’ data. Telegram controls send only the boolean preference with the existing CSRF token.

Historical-analysis presentation receives only the approved owner-scoped run/report/trade/equity contract, keeps run IDs, fingerprints, reports, series, and idempotency keys in memory, and never stores them in browser persistence. It does not calculate indicators or metrics and does not contact Binance or Telegram.

Repository-owned UI primitives, theme controls, and toast composition do not log component props, API responses, authentication values, or Telegram data, and no analytics or telemetry dependency is added.

## Current Limitations and Unresolved Risks

Rate limits are process-local. There is no documented production backup, account-deletion, distributed rate-limit, security-review, penetration-test, or provider-verification outcome. Runtime CORS/cookie deployment values require an explicit operational review before exposure beyond the configured origin.

## Verification Status

Security behavior was inspected statically from code and configuration. No penetration test, provider request, browser flow, migration, or runtime security verification was run.
