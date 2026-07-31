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

`POST /telegram/link-tokens` returns `201 {connection:{status,linkExpiresAt},telegramUrl}`; it requires configured bot identity, authentication, CSRF, and local user/IP limits. `GET /telegram/connection` returns `200 {connection:{status,username,connectedAt,lastVerifiedAt,linkExpiresAt,statusReason}}`. `DELETE /telegram/connection` returns `204` and is owner-scoped.

`POST /telegram/test-notifications` requires `Idempotency-Key` as a UUID and returns `202 {notification:{id,status,createdAt,sentAt,failureCode}}`; a replay returns the same outbox item. `GET /telegram/test-notifications/{id}` returns its own notification only. Invalid idempotency is `400 TELEGRAM_TEST_IDEMPOTENCY_KEY_INVALID`.

## Supported Markets

`GET /markets` returns `200 {markets:[{exchange,marketType,symbol,baseAsset,quoteAsset,status,priceRules,metadataCheckedAt}]}`. Available rows include `{min,max,tick}` exact-decimal strings; unavailable rows omit price rules. It is public and cached for 60 seconds.

## One-Time Price Alerts

`POST /alerts/price` needs auth, CSRF, and UUID `Idempotency-Key`; body is `{exchange,marketType,symbol,direction,target_price}` with `direction` `cross_above` or `cross_below`. It returns `201` for a new alert or `200` for an identical replay. The response is `{alert:{id,type:"price_cross",market,direction,targetPrice,status,statusReason,evaluationReady,lastObservedPrice,createdAt,trigger,delivery,marketData}}`.

`GET /alerts` accepts `limit`, opaque `cursor`, and optional `status`, returning `{alerts,nextCursor}`. `GET /alerts/{id}` returns one envelope. `DELETE /alerts/{id}` returns `204`; all reads/writes are owner scoped. Creation and deletion have local limits; malformed bodies/IDs and unavailable markets use the price-alert service’s safe stable errors.

## Signal Presets and Subscriptions

`GET /signal-presets` returns the public cached `{presets:[{code,version,name,description,strategyType,timeframe,direction,parameters:{period,threshold,priceInput},status:"available"}]}`.

`GET /signal-subscriptions` returns `{subscriptions:[{id,status,statusReason,market,preset,activatedAt,disabledAt}]}` for the principal. `POST /signal-subscriptions` needs auth and CSRF; body is `{exchange,market_type,symbol,preset_code,preset_version}` and returns `201` or `200` when reactivating/idempotently replaying the user’s existing combination. `DELETE /signal-subscriptions/{id}` returns `204`. Invalid subscription input is `422 SIGNAL_PRESET_UNAVAILABLE`; access is owner scoped and enable/disable limits are local.

## Ownership and Information-Exposure Rules

The authenticated session selects the user ID; callers never supply it. Alert, subscription, Telegram connection, and notification reads/mutations are filtered by that ID. Responses omit tokens, password hashes, bot credentials, raw provider payloads, and internal evaluator state.

## Rate-Limit Summary

Authentication, Telegram, alerts, and subscription operations use independent 15-minute in-memory buckets. A rate-limited response includes `Retry-After` only where the service produces it. Limits do not coordinate across processes.

## Contract-Change Rule

Route, schema, error, cache, authorization, pagination, or rate-limit changes require this document and browser-consumer updates in the same change.

## Verification Status

These contracts were read from routes, schemas, services, and browser consumers; no API, browser, or runtime verification was run.
