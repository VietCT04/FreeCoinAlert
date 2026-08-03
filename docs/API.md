# API

## Purpose and Base Conventions

The FastAPI API has no version prefix. JSON field names are camelCase unless stated otherwise. Unknown fields are rejected for credential, alert, and signal-subscription bodies, including the Telegram-delivery preference update. UUIDs and timestamps serialize as JSON strings; monetary and indicator values serialize as decimal strings.

## Authentication, Cookie, CSRF, Origin, and Cache Rules

Authenticated requests use the `freecoinalert_session` HTTP-only, `SameSite=Lax`, path `/` cookie. The secure flag follows `SESSION_COOKIE_SECURE`. Mutating authenticated endpoints require `X-CSRF-Token`; `/auth/register` and `/auth/login` instead validate a supplied `Origin` when present. CORS permits only `WEB_ORIGIN`, credentials, `GET`/`POST`/`PUT`/`DELETE`, and `Content-Type`, `Idempotency-Key`, `Last-Event-ID`, and `X-CSRF-Token`. Private responses use `Cache-Control: no-store`; public catalogue/preset lists use `public, max-age=60`.

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
| GET/POST/DELETE/PUT | `/signal-subscriptions`, `/signal-subscriptions`, `/signal-subscriptions/{id}`, `/signal-subscriptions/{id}/telegram-delivery` | yes / post+delete+put | subscriptions and Telegram-delivery preference |
| GET/GET | `/signal-feed`, `/signal-feed/stream` | yes / no | historical and live signal feed |
| POST/GET/DELETE | `/telegram/link-tokens`, `/telegram/connection`, `/telegram/connection` | yes / post+delete | Telegram connection |
| POST/GET | `/telegram/test-notifications`, `/telegram/test-notifications/{id}` | yes / post only | test delivery |

## Health

`GET /health` returns `200 {"status":"ok","service":"freecoinalert-api"}`. It is process liveness only; it does not prove database, provider, or worker health.

## Authentication

`POST /auth/register` returns `201`, and `POST /auth/login` returns `200`, with `{user:{id,email,createdAt},csrfToken}` and sets a host-only session cookie with no `Expires` or `Max-Age`. Body `{email,password}` rejects unknown fields; email is normalized for identity and password must be 15–128 characters. Registration allows 5 attempts per direct IP per 15 minutes. Login allows 10 attempts per direct IP and 5 failed attempts per normalized email/direct-IP pair in the same window. Registration rejects an existing email with `409 AUTH_REGISTRATION_UNAVAILABLE`; invalid credentials are `401 AUTH_INVALID_CREDENTIALS`; invalid bodies/passwords are `422 AUTH_REQUEST_INVALID`; disallowed origin is `403 AUTH_ORIGIN_REJECTED`; limits return `429 AUTH_RATE_LIMITED` with `Retry-After`.

`GET /auth/me` returns the same body for an active unexpired, unrevoked session. Missing, malformed, unknown, expired, or revoked cookies return `401 AUTHENTICATION_REQUIRED` and clear the stale session cookie where that response is produced. `POST /auth/logout` requires a valid `X-CSRF-Token` for a live session, revokes only that session, clears the cookie, and returns `204`; absent/invalid sessions also return `204` and clear the cookie without revealing whether a session existed. A live session with an invalid/missing CSRF header returns `403 AUTH_CSRF_INVALID` and is not revoked. Session expiry is fixed by `SESSION_TTL_SECONDS` (default seven days) and ordinary requests do not extend it.

## Telegram

`POST /telegram/link-tokens` accepts no body and returns `201 {connection:{status:"linking",linkExpiresAt},telegramUrl}`. It requires configured bot identity, authentication, CSRF, and local limits of 5 per user and 10 per direct IP per 15 minutes; a limit response is `429 TELEGRAM_LINK_RATE_LIMITED` with `Retry-After`. It returns `503 TELEGRAM_NOT_CONFIGURED` without bot configuration, `409 TELEGRAM_ALREADY_CONNECTED` for a connected/degraded destination, and `503 TELEGRAM_LINK_UNAVAILABLE` for storage conflicts/failure. The raw deep-link token is returned only in `telegramUrl`.

`GET /telegram/connection` returns `200 {connection:{status,username,connectedAt,lastVerifiedAt,linkExpiresAt,statusReason}}` for its authenticated owner, with `linking` derived from an active link token. `DELETE /telegram/connection` needs CSRF, accepts no body, is limited to 10 per user per 15 minutes, revokes outstanding link tokens, and returns `204`; it is idempotent for no connection or a disconnected connection. Storage failure is `503 TELEGRAM_CONNECTION_UNAVAILABLE`.

`POST /telegram/test-notifications` requires authentication, `X-CSRF-Token`, UUID `Idempotency-Key`, and no request body. It returns `202 {notification:{id,status,createdAt,sentAt,failureCode}}`; status is `queued`, `sending`, `retrying`, `sent`, or `failed`, and a same-user key replay returns the existing outbox item without another queue entry. New requests are limited to 3 per user per 15 minutes. Invalid/missing idempotency is `400 TELEGRAM_TEST_IDEMPOTENCY_KEY_INVALID`; disconnected and degraded destinations return `409 TELEGRAM_NOT_CONNECTED` and `409 TELEGRAM_CONNECTION_DEGRADED`; storage/queue failure returns `503 TELEGRAM_NOTIFICATION_UNAVAILABLE`.

`GET /telegram/test-notifications/{id}` requires authentication and returns that user’s same safe notification envelope with `no-store`; a missing or foreign ID is `404 TELEGRAM_NOTIFICATION_NOT_FOUND`.

## Supported Markets

`GET /markets` returns `200 {markets:[{exchange,marketType,symbol,baseAsset,quoteAsset,status,priceRules,metadataCheckedAt}]}`. Available rows include `{min,max,tick}` exact-decimal strings; unavailable rows return `priceRules: null`. It is public and cached for 60 seconds.

## One-Time Price Alerts

`POST /alerts/price` needs auth, CSRF, and an `Idempotency-Key` UUID (maximum 128 characters). Its JSON body forbids unknown fields and is `{exchange,market_type,symbol,direction,target_price}`; direction is `cross_above` or `cross_below`, while target price is a positive plain decimal with at most 18 fraction digits, within the catalogue range, and aligned to the market tick. It returns `201` for a new alert or `200` for an identical replay, each with `{alert:{id,type:"price_cross",market,direction,targetPrice,status,statusReason,evaluationReady,lastObservedPrice,createdAt,trigger,delivery,marketData}}` and `no-store`.

Creation is limited to 10 per user and 30 per direct client IP per 15 minutes, and permits at most 20 active alerts per user. The user needs a connected Telegram destination; disconnected returns `409 ALERT_TELEGRAM_NOT_CONNECTED` and degraded returns `409 ALERT_TELEGRAM_DEGRADED`. Other stable creation errors are `422 ALERT_IDEMPOTENCY_KEY_INVALID`, `422 ALERT_REQUEST_INVALID`, `422 ALERT_TARGET_INVALID`, `422 ALERT_MARKET_UNAVAILABLE`, `409 ALERT_ACTIVE_LIMIT_REACHED`, `409 ALERT_IDEMPOTENCY_CONFLICT` when a replay key has a different request, and `503 ALERT_UNAVAILABLE` for persistence unavailability.

`GET /alerts` accepts an optional `limit` (default `20`, integer `1`–`50` without alternate spelling), an opaque `cursor`, and optional status `active`, `triggered`, `disabled`, or `failed`; it returns `{alerts,nextCursor}` ordered by creation time/id descending. A malformed limit, status, or cursor returns `422 ALERT_REQUEST_INVALID` or `422 ALERT_CURSOR_INVALID`; the cursor encodes the last row’s UTC creation time and UUID. `GET /alerts/{id}` returns one owned alert envelope; a malformed ID is `422 ALERT_REQUEST_INVALID`, missing or foreign IDs are `404 ALERT_NOT_FOUND`. `DELETE /alerts/{id}` needs CSRF, is limited to 30 per user per 15 minutes, returns `204` for a successful or replayed deletion, and returns `409 ALERT_NOT_DELETABLE` for triggered/failed alerts. All alert reads and writes are owner scoped and `no-store`; `503 ALERT_UNAVAILABLE` is the safe storage failure response.

## Signal Presets and Subscriptions

`GET /signal-presets` returns the public cached `{presets:[{code,version,name,description,strategyType,timeframe,direction,parameters:{period,threshold,priceInput},status:"available"}]}`.

`GET /signal-subscriptions` returns `{subscriptions:[{id,status,statusReason,market,preset,telegramDelivery,activatedAt,disabledAt}]}` for the principal. `telegramDelivery` is `{enabled,readiness,statusReason,changedAt}`. `readiness` is `ready` for a connected private destination, `degraded` for a degraded destination, `linking` when an unexpired link token exists without a usable destination, and `not_connected` otherwise. Readiness is resolved dynamically once for the request and is not persisted on the subscription. No Telegram user ID, chat ID, token, or provider response is returned.

`POST /signal-subscriptions` needs auth and CSRF; its body forbids unknown fields and is `{exchange,market_type,symbol,preset_code,preset_version}`. It returns `201` for a new row and `200` for an already-active replay or reactivation. It is limited to 20 enables per user and 40 per direct IP per 15 minutes, plus a maximum of 20 active subscriptions per user; rate limiting is `429 SIGNAL_SUBSCRIPTION_RATE_LIMITED` with `Retry-After`. New subscriptions and reactivations reset Telegram delivery to disabled. Stable failures are `422 SIGNAL_PRESET_UNAVAILABLE` for malformed input, `404 SIGNAL_PRESET_NOT_FOUND`, `409 SIGNAL_PRESET_UNAVAILABLE`, `422 SIGNAL_MARKET_UNAVAILABLE`, `409 SIGNAL_SUBSCRIPTION_LIMIT_REACHED`, and `503 SIGNAL_SUBSCRIPTION_UNAVAILABLE`.

`DELETE /signal-subscriptions/{id}` needs CSRF, is limited to 30 per user per 15 minutes, returns `204` for the owner (including an already-disabled row), and returns `404 SIGNAL_SUBSCRIPTION_NOT_FOUND` for missing or foreign IDs. Disabling an active subscription resets Telegram delivery to disabled and records the occurrence-time subscription state. All subscription results are owner-scoped and `no-store`.

`PUT /signal-subscriptions/{id}/telegram-delivery` needs authentication and CSRF, accepts only `{enabled:boolean}`, rejects unknown fields, and returns `200` with the complete updated subscription envelope and `Cache-Control: no-store`. It is limited to 30 preference mutations per user per 15 minutes. Enabling is allowed only for an active subscription with a connected, non-degraded Telegram destination; linking and disconnected states return `409 SIGNAL_TELEGRAM_NOT_CONNECTED`, while degraded state returns `409 SIGNAL_TELEGRAM_DEGRADED`. Disabling is always allowed and idempotent. Repeated equivalent requests return `200` without another state-history row. Stable failures are `422 SIGNAL_TELEGRAM_DELIVERY_REQUEST_INVALID`, `404 SIGNAL_SUBSCRIPTION_NOT_FOUND`, `409 SIGNAL_SUBSCRIPTION_INACTIVE`, `409 SIGNAL_TELEGRAM_NOT_CONNECTED`, `409 SIGNAL_TELEGRAM_DEGRADED`, `429 SIGNAL_TELEGRAM_DELIVERY_RATE_LIMITED`, and `503 SIGNAL_SUBSCRIPTION_UNAVAILABLE`.

Every subscription lifecycle or preference transition records an immutable occurrence-time state row in the same transaction. This API stores intent and readiness only; it does not create notification-outbox jobs, send Telegram messages, or replay historical signal occurrences. A separate database dispatcher consumes new live occurrences and may create internal `telegram_preset_signal` jobs, which the notification worker may later deliver; no dispatch or per-occurrence provider-delivery state is exposed through this HTTP contract.

## Historical Signal Feed

`GET /signal-feed` requires the authenticated session and does not require CSRF. It is limited to 120 requests per authenticated user per 15 minutes. Query parameters are `limit` (default 50, range 1â€“100), an opaque `cursor`, and `status` (`current`, `invalidated`, or `all`; default `current`). Results are visible only when the authenticated user has an active or disabled subscription matching the event's market and preset. A subscription may grant historical visibility to occurrences that predate its activation; this does not claim that the occurrence was delivered at that time.

Events are ordered by `occurredAt DESC, id DESC`. The cursor encodes the last occurred-at/UUID pair and is rejected as `422 SIGNAL_FEED_CURSOR_INVALID` when malformed. The response is:

```json
{
  "events": [
    {
      "id": "signal event UUID",
      "status": "current",
      "invalidationReason": null,
      "market": {
        "exchange": "binance",
        "marketType": "spot",
        "symbol": "BTCUSDT",
        "baseAsset": "BTC",
        "quoteAsset": "USDT"
      },
      "preset": {
        "code": "price_sma_200_cross_below_1h",
        "version": 1,
        "name": "Price crosses below SMA 200",
        "strategyType": "price_sma_cross",
        "timeframe": "1h",
        "direction": "cross_below",
        "parameters": {
          "period": 200,
          "threshold": null,
          "priceInput": "close"
        }
      },
      "comparison": {
        "leftLabel": "price",
        "rightLabel": "sma_200",
        "previousLeft": "exact decimal string",
        "previousRight": "exact decimal string",
        "currentLeft": "exact decimal string",
        "currentRight": "exact decimal string"
      },
      "candle": {
        "revision": 1,
        "closePrice": "exact decimal string",
        "openTime": "UTC timestamp",
        "closeTime": "UTC timestamp"
      },
      "backfilled": true,
      "occurredAt": "UTC timestamp",
      "recordedAt": "UTC timestamp"
    }
  ],
  "nextCursor": null,
  "streamCursor": "12345"
}
```

All numeric values are canonical decimal strings. The response never exposes internal market, preset, subscription, or user IDs; calculation-state JSON; provider payloads; Telegram state; or arbitrary invalidation text. The safe invalidation messages are fixed for `candle_corrected`, `calculation_invariant`, and `preset_disabled`. Responses use `Cache-Control: no-store`.

`streamCursor` is the latest global durable feed sequence observed in the same request transaction. It is a recovery watermark, not a claim that every lower sequence was visible to the user.

## Live Signal Feed Stream

`GET /signal-feed/stream` requires the authenticated session cookie and does not require CSRF. It accepts optional `after=<non-negative stream sequence>`. A valid `Last-Event-ID` header and `after` value are combined by using the greater sequence; malformed values are rejected before streaming as `422 SIGNAL_FEED_STREAM_CURSOR_INVALID`.

The response is credentialed SSE with `Content-Type: text/event-stream`, `Cache-Control: no-store, no-transform`, `Connection: keep-alive`, and `X-Accel-Buffering: no`. It begins with `retry: 5000`. Event types are `signal`, `signal_invalidated`, `reset`, and `auth_expired`. Signal and invalidation data include `deliveryMode: live | replay` and the stream sequence is the SSE event ID. A reset tells the browser to reload `/signal-feed`; authentication expiry tells it to stop using the connection until a fresh session is available. Heartbeats are `: heartbeat` comments at least every `SIGNAL_SSE_HEARTBEAT_SECONDS` (15 seconds by default).

Replay reads durable stream rows above the resume sequence, filters them through currently active matching subscriptions, and sends at most 100 visible records as `deliveryMode: replay` before joining the live queue. A resume cursor older than the retained stream log or a replay larger than 100 records produces `reset` and closes the connection. Disabled subscriptions grant history visibility but receive no new live or replay stream events. The browser can recover through the historical endpoint without duplicate entries.

The stream allows 10 connection attempts per user and 30 per direct client IP per 15 minutes, returns `429 SIGNAL_FEED_RATE_LIMITED` with `Retry-After` when those buckets are exhausted, and permits at most 2 concurrent connections per user and 500 per API process. A slow connection has a queue of 100 sequence integers; queue overflow emits `reset` when possible and closes the connection rather than silently dropping an event. Limits and connection counts are process-local until shared infrastructure is approved.

Stable feed errors are `SIGNAL_FEED_CURSOR_INVALID`, `SIGNAL_FEED_STREAM_CURSOR_INVALID`, `SIGNAL_FEED_REQUEST_INVALID`, `SIGNAL_FEED_RATE_LIMITED`, `SIGNAL_FEED_CONNECTION_LIMIT_REACHED`, and `SIGNAL_FEED_UNAVAILABLE`. Once streaming starts, control events and connection close replace a JSON error response.

The authenticated root browser surface consumes these contracts with native credentialed Fetch and `EventSource`. It keeps the historical pagination cursor separate from the `streamCursor` watermark, closes the stream when the document is hidden, refreshes history before visibility recovery, and treats replay or recovery entries as non-live UI updates. Active preset cards use the server-owned Telegram-delivery preference endpoint with the existing CSRF token, confirm enabling, apply only successful responses, and refresh subscriptions after Telegram connection changes. Browser sound is an optional client-side presentation feature and is not part of the API or Telegram delivery contract.

## Ownership and Information-Exposure Rules

The authenticated session selects the user ID; callers never supply it. Alert, subscription, signal-feed, Telegram connection, and notification reads/mutations are filtered by that ID. Responses omit tokens, password hashes, bot credentials, raw provider payloads, and internal evaluator state.

## Rate-Limit Summary

Authentication, Telegram, alerts, and subscription operations use independent 15-minute in-memory buckets. A rate-limited response includes `Retry-After` only where the service produces it. Limits do not coordinate across processes.

## Contract-Change Rule

Route, schema, error, cache, authorization, pagination, or rate-limit changes require this document and browser-consumer updates in the same change.

## Verification Status

These contracts were read from routes, schemas, services, and browser consumers; no API, browser, or runtime verification was run.
