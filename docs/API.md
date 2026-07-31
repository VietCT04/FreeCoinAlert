# API

## Purpose and Base Conventions

The FastAPI API has no version prefix. JSON field names are camelCase unless stated otherwise. Unknown fields are rejected for credential, alert, and subscription creation bodies. UUIDs and timestamps serialize as JSON strings; monetary and indicator values serialize as decimal strings.

## Authentication, Cookie, CSRF, Origin, and Cache Rules

Authenticated requests use the `freecoinalert_session` HTTP-only, `SameSite=Lax`, path `/` cookie. The secure flag follows `SESSION_COOKIE_SECURE`. Mutating authenticated endpoints require `X-CSRF-Token`; `/auth/register` and `/auth/login` instead validate a supplied `Origin` when present. CORS permits only `WEB_ORIGIN`, credentials, `GET`/`POST`/`DELETE`, and `Content-Type`, `Idempotency-Key`, and `X-CSRF-Token`. Private responses use `Cache-Control: no-store`; public catalogue/preset lists use `public, max-age=60`.

## Error Contract

Authentication errors are `{ "code": string, "message": string, "details": [] }`, with `Cache-Control: no-store` and `Retry-After` for rate limits. Authentication request validation is `422 AUTH_REQUEST_INVALID`; non-auth FastAPI validation is `{ "detail": "Request validation failed." }`. Domain services return their documented stable code and safe message; unknown foreign resources are not disclosed as owned.

## Endpoint Index

| Method | Path | Auth / CSRF | Result |
| --- | --- | --- | --- |
| GET | `/health` | no / no | API liveness |
| POST | `/auth/register`, `/auth/login` | no / origin | session creation |
| GET | `/auth/me` | yes / no | user and CSRF token |
| POST | `/auth/logout` | cookie / yes | session revocation |
| GET | `/markets` | no / no | supported markets |
| POST/GET/GET/DELETE | `/alerts/price`, `/alerts`, `/alerts/{id}`, `/alerts/{id}` | yes / post+delete | one-time alerts |
| GET | `/signal-presets` | no / no | preset catalogue |
| GET/POST/DELETE | `/signal-subscriptions`, `/signal-subscriptions`, `/signal-subscriptions/{id}` | yes / post+delete | subscriptions |
| POST/GET/DELETE | `/telegram/link-tokens`, `/telegram/connection`, `/telegram/connection` | yes / post+delete | Telegram connection |
| POST/GET | `/telegram/test-notifications`, `/telegram/test-notifications/{id}` | yes / post only | test delivery |

## Health

`GET /health` returns `200 {"status":"ok","service":"freecoinalert-api"}`. It is process liveness only; it does not prove database, provider, or worker health.

## Authentication

`POST /auth/register` returns `201`, and `POST /auth/login` returns `200`, with `{user:{id,email,createdAt},csrfToken}` and sets the session cookie. Body: `{email,password}`. Registration rejects an existing email with `409 AUTH_REGISTRATION_UNAVAILABLE`; invalid credentials are `401 AUTH_INVALID_CREDENTIALS`; disallowed origin is `403 AUTH_ORIGIN_REJECTED`; limits return `429 AUTH_RATE_LIMITED`. `GET /auth/me` returns the same body. `POST /auth/logout` returns `204`, is idempotent for absent/invalid sessions, and clears the cookie; a live session needs a valid CSRF token.

## Telegram

`POST /telegram/link-tokens` accepts no body and returns `201 {connection:{status:"linking",linkExpiresAt},telegramUrl}`. It requires configured bot identity, authentication, CSRF, and local limits of 5 per user and 10 per direct IP per 15 minutes; a limit response is `429 TELEGRAM_LINK_RATE_LIMITED` with `Retry-After`. It returns `503 TELEGRAM_NOT_CONFIGURED` without bot configuration, `409 TELEGRAM_ALREADY_CONNECTED` for a connected/degraded destination, and `503 TELEGRAM_LINK_UNAVAILABLE` for storage conflicts/failure. The raw deep-link token is returned only in `telegramUrl`.

`GET /telegram/connection` returns `200 {connection:{status,username,connectedAt,lastVerifiedAt,linkExpiresAt,statusReason}}` for its authenticated owner, with `linking` derived from an active link token. `DELETE /telegram/connection` needs CSRF, accepts no body, is limited to 10 per user per 15 minutes, revokes outstanding link tokens, and returns `204`; it is idempotent for no connection or a disconnected connection. Storage failure is `503 TELEGRAM_CONNECTION_UNAVAILABLE`.

`POST /telegram/test-notifications` requires `Idempotency-Key` as a UUID and returns `202 {notification:{id,status,createdAt,sentAt,failureCode}}`; a replay returns the same outbox item. `GET /telegram/test-notifications/{id}` returns its own notification only. Invalid idempotency is `400 TELEGRAM_TEST_IDEMPOTENCY_KEY_INVALID`.

## Supported Markets

`GET /markets` returns `200 {markets:[{exchange,marketType,symbol,baseAsset,quoteAsset,status,priceRules,metadataCheckedAt}]}`. Available rows include `{min,max,tick}` exact-decimal strings; unavailable rows return `priceRules: null`. It is public and cached for 60 seconds.

## One-Time Price Alerts

`POST /alerts/price` needs auth, CSRF, and an `Idempotency-Key` UUID (maximum 128 characters). Its JSON body forbids unknown fields and is `{exchange,market_type,symbol,direction,target_price}`; direction is `cross_above` or `cross_below`, while target price is a positive plain decimal with at most 18 fraction digits, within the catalogue range, and aligned to the market tick. It returns `201` for a new alert or `200` for an identical replay, each with `{alert:{id,type:"price_cross",market,direction,targetPrice,status,statusReason,evaluationReady,lastObservedPrice,createdAt,trigger,delivery,marketData}}` and `no-store`.

Creation is limited to 10 per user and 30 per direct client IP per 15 minutes, and permits at most 20 active alerts per user. The user needs a connected Telegram destination; disconnected returns `409 ALERT_TELEGRAM_NOT_CONNECTED` and degraded returns `409 ALERT_TELEGRAM_DEGRADED`. Other stable creation errors are `422 ALERT_IDEMPOTENCY_KEY_INVALID`, `422 ALERT_REQUEST_INVALID`, `422 ALERT_TARGET_INVALID`, `422 ALERT_MARKET_UNAVAILABLE`, `409 ALERT_ACTIVE_LIMIT_REACHED`, `409 ALERT_IDEMPOTENCY_CONFLICT` when a replay key has a different request, and `503 ALERT_UNAVAILABLE` for persistence unavailability.

`GET /alerts` accepts an optional `limit` (default `20`, integer `1`–`50` without alternate spelling), an opaque `cursor`, and optional status `active`, `triggered`, `disabled`, or `failed`; it returns `{alerts,nextCursor}` ordered by creation time/id descending. A malformed limit, status, or cursor returns `422 ALERT_REQUEST_INVALID` or `422 ALERT_CURSOR_INVALID`; the cursor encodes the last row’s UTC creation time and UUID. `GET /alerts/{id}` returns one owned alert envelope; a malformed ID is `422 ALERT_REQUEST_INVALID`, missing or foreign IDs are `404 ALERT_NOT_FOUND`. `DELETE /alerts/{id}` needs CSRF, is limited to 30 per user per 15 minutes, returns `204` for a successful or replayed deletion, and returns `409 ALERT_NOT_DELETABLE` for triggered/failed alerts. All alert reads and writes are owner scoped and `no-store`; `503 ALERT_UNAVAILABLE` is the safe storage failure response.

## Signal Presets and Subscriptions

`GET /signal-presets` returns the public cached `{presets:[{code,version,name,description,strategyType,timeframe,direction,parameters:{period,threshold,priceInput},status:"available"}]}`.

`GET /signal-subscriptions` returns `{subscriptions:[{id,status,statusReason,market,preset,activatedAt,disabledAt}]}` for the principal. `POST /signal-subscriptions` needs auth and CSRF; its body forbids unknown fields and is `{exchange,market_type,symbol,preset_code,preset_version}`. It returns `201` for a new row and `200` for an already-active replay or reactivation. It is limited to 20 enables per user and 40 per direct IP per 15 minutes, plus a maximum of 20 active subscriptions per user; rate limiting is `429 SIGNAL_SUBSCRIPTION_RATE_LIMITED` with `Retry-After`. Stable failures are `422 SIGNAL_PRESET_UNAVAILABLE` for malformed input, `404 SIGNAL_PRESET_NOT_FOUND`, `409 SIGNAL_PRESET_UNAVAILABLE`, `422 SIGNAL_MARKET_UNAVAILABLE`, `409 SIGNAL_SUBSCRIPTION_LIMIT_REACHED`, and `503 SIGNAL_SUBSCRIPTION_UNAVAILABLE`.

`DELETE /signal-subscriptions/{id}` needs CSRF, is limited to 30 per user per 15 minutes, returns `204` for the owner (including an already-disabled row), and returns `404 SIGNAL_SUBSCRIPTION_NOT_FOUND` for missing or foreign IDs. All subscription results are owner-scoped and `no-store`.

## Ownership and Information-Exposure Rules

The authenticated session selects the user ID; callers never supply it. Alert, subscription, Telegram connection, and notification reads/mutations are filtered by that ID. Responses omit tokens, password hashes, bot credentials, raw provider payloads, and internal evaluator state.

## Rate-Limit Summary

Authentication, Telegram, alerts, and subscription operations use independent 15-minute in-memory buckets. A rate-limited response includes `Retry-After` only where the service produces it. Limits do not coordinate across processes.

## Contract-Change Rule

Route, schema, error, cache, authorization, pagination, or rate-limit changes require this document and browser-consumer updates in the same change.

## Verification Status

These contracts were read from routes, schemas, services, and browser consumers; no API, browser, or runtime verification was run.
