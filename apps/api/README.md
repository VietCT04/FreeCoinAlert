# FreeCoinAlert API

The API is the Python and FastAPI foundation for FreeCoinAlert. It includes user and
authentication-session persistence, unauthenticated process health, account
registration, sign-in, current-user lookup, logout, authenticated Telegram link-token,
connection-state, and disconnect APIs, plus a separately runnable Telegram update processor.
It also has a durable Telegram test-notification outbox and separately runnable delivery worker.
It provides a fixed Binance Spot market catalog with a public read endpoint and an explicit metadata
synchronization command. It also includes the optional centralized live price stream and its one-time price-alert
evaluator; alert creation remains an authenticated API concern.

## Prerequisites

- CPython 3.14
- [uv](https://docs.astral.sh/uv/)

The required Python version is recorded in `.python-version`. uv manages the Python
environment, dependencies, and lockfile for this component.

## Setup and local startup

From `apps/api`:

```bash
uv sync
uv run fastapi dev src/freecoinalert_api/main.py --host 0.0.0.0 --port 8000
```

Copy `.env.example` to a local `.env` before using database commands. Direct-host
development uses `localhost` in `DATABASE_URL`; the Compose-only `db` hostname is not
valid when the API runs directly on the host.

The API listens on `http://localhost:8000`. FastAPI's standard documentation remains
available at `/docs`, `/redoc`, and `/openapi.json`.

## Integrated Compose Startup

From the repository root, copy `.env.example` to `.env` and run `pnpm dev` to start the API with the web application and local PostgreSQL stack. The API container binds only to `127.0.0.1` on the configured `API_PORT` (default `8000`), receives its `DATABASE_URL` through the internal `db` service hostname, and waits for PostgreSQL to be healthy. The local-development container command applies `alembic upgrade head` before FastAPI starts; this is not a production deployment command. `/health` remains API-process liveness only and never queries PostgreSQL.

## Database commands

From the repository root:

```bash
pnpm db:migrate
pnpm db:revision -- -m "describe the change"
```

`db:migrate` explicitly applies the current Alembic migration head. Review and apply
production migrations through a production release process; they are never applied by
an API production command.

## Component commands

```bash
uv run ruff check .
uv run ruff format .
uv run ruff format --check .
uv run mypy src
uv run python -m freecoinalert_api.market_data.catalog_sync
```

## Source layout

`src/freecoinalert_api/main.py` owns the application factory and ASGI application.
`api/routes/auth.py` provides registration, sign-in, current-user lookup, and logout;
`api/routes/telegram.py` provides authenticated link-token, state, and disconnect routes.
`auth/` contains focused email, origin, password, rate-limit, session, and
authenticated-principal helpers. `core/config.py` reads
database and browser-authentication settings; `db/` owns typed SQLAlchemy models,
asynchronous sessions, repositories, and Alembic migrations. Telegram persistence is
limited to the `telegram_connections`, `telegram_link_tokens`, and
`telegram_processed_updates` models and repository operations. `telegram/` owns safe
one-time token creation, link and disconnect transactions, a bounded local limiter, the Bot API
client boundary, private `/start` parsing, atomic update linking, and the local polling executable.
It does not expose a webhook endpoint or implement alert notification delivery.

`market_data/` owns the centralized unauthenticated Binance public REST boundary and the supported-market
catalog service. It is limited to the approved Binance Spot USDT allowlist (`BTCUSDT`, `ETHUSDT`,
`BNBUSDT`, `SOLUSDT`, and `XRPUSDT`) and does not start a WebSocket, backfill history, or create alerts.

## Environment rules

Keep component-specific variables in `.env` files that are not committed. Use
`.env.example` only for safe, consumed variable names and comments. The API consumes
`DATABASE_URL`, `WEB_ORIGIN`, `SESSION_COOKIE_SECURE`, `SESSION_TTL_SECONDS`,
`TELEGRAM_BOT_USERNAME`, `TELEGRAM_LINK_TTL_SECONDS`, `TELEGRAM_BOT_TOKEN`, and
`TELEGRAM_UPDATE_RETENTION_DAYS`; they
must contain no production credentials in committed files. The local browser defaults
are `http://localhost:3000`, `false`, and seven days (`604800`) respectively.

`TELEGRAM_BOT_USERNAME` is optional, public configuration with no leading `@` and only
Telegram username characters. If it is absent, link creation returns a safe `503` response.
`TELEGRAM_LINK_TTL_SECONDS` defaults to 600. `TELEGRAM_BOT_TOKEN` is a secret required only
by `python -m freecoinalert_api.telegram.poller`; normal API startup does not require it.
`TELEGRAM_UPDATE_RETENTION_DAYS` defaults to 30.

`CANDLE_RETENTION_DAYS` defaults to 180 and is consumed as the future explicit cutoff for candle-revision cleanup. This issue creates the persistence and cleanup boundary only; it does not run cleanup, ingest Binance klines, bootstrap history, aggregate windows, or calculate indicators.

`BINANCE_SPOT_BASE_URL` defaults to `https://api.binance.com` and has no credentials. The public
catalog considers metadata stale after `MARKET_CATALOG_MAX_AGE_SECONDS` (default `86400`). Normal API
startup never contacts Binance. Run `uv run python -m freecoinalert_api.market_data.catalog_sync` only
as an explicit operator action; it requests metadata for exactly the five allowlisted Spot symbols in one
call and preserves the last valid catalog when the provider or database operation fails.

## Supported market catalog

`GET /markets` is public, read-only, and cached for 60 seconds. It always returns the five approved
Binance Spot symbols in deterministic symbol order. A market is `available` only when it is product-enabled,
trading, has complete valid price rules, and its metadata is not stale; otherwise the API returns the safe
`unavailable` state with `priceRules: null`. Decimal rules are JSON strings, never floating-point numbers.

## Telegram connection endpoints

`POST /telegram/link-tokens` requires the HTTP-only session and `X-CSRF-Token`, returns a
one-time deep link plus `linking` expiry, and commits its SHA-256 token hash before returning.
The raw token appears only in that URL. `GET /telegram/connection` returns the current user's
safe status only. `DELETE /telegram/connection` requires CSRF, idempotently disconnects the
current saved destination, and revokes outstanding tokens. All connection responses use
`Cache-Control: no-store` and never expose chat IDs, Telegram user IDs, hashes, or raw tokens.

The local in-memory limiter permits five link requests per user and ten per direct client IP,
plus ten disconnect requests per user, in fifteen minutes. It is not sufficient for multiple
API replicas or an untrusted proxy deployment.

## Telegram update processor

Run `uv run python -m freecoinalert_api.telegram.poller` only for local Telegram long polling.
It requests message updates, processes them sequentially, accepts private-chat `/start <token>`
or addressed `/start@<bot_username> <token>` commands only, and uses `update_id` as the database
idempotency key. The processor commits linking before one confirmation attempt; it records a
confirmed send but does not retry a timeout or uncertain outcome. It performs bounded processed-
update cleanup at startup and no more than daily. Production webhook deployment, groups, channels,
and test-notification delivery remain out of scope.

## Telegram notification worker

`uv run python -m freecoinalert_api.notifications.worker` processes the durable test-notification
outbox. It claims jobs in short transactions, rechecks the connected owned destination before a
provider request, records confirmed sends, applies bounded retries for known temporary failures,
and records timeouts as outcome-unknown failures to avoid duplicate messages. The worker requires
`TELEGRAM_BOT_TOKEN`; API startup does not. It must not be run as part of routine implementation.

## Authentication endpoints

`POST /auth/register` returns `201`; `POST /auth/login` returns `200`. Both accept
`email` and `password` JSON fields, return a safe user object plus `csrfToken`, and set
an HTTP-only `freecoinalert_session` browser-session cookie. Passwords allow Unicode and
spaces without trimming and must be 15–128 Unicode code points. Emails are trimmed,
normalized without DNS or deliverability checks, then case-folded for unique identity.

The API uses Argon2id password hashes, stores only a SHA-256 session-token hash, and
enforces a seven-day absolute session expiry. Authentication and logout responses include
`Cache-Control: no-store`. `GET /auth/me` restores the safe current user and the session
CSRF token after a browser refresh. `POST /auth/logout` requires that CSRF token in
`X-CSRF-Token`, revokes only the current session, clears the cookie, and returns `204`;
absent or stale sessions also return `204` after clearing the cookie. Future
cookie-authenticated ownership checks use the server-side immutable authenticated
principal rather than client-supplied user IDs. The local limiter allows five registration
attempts per IP, ten login attempts per IP, and five failed login attempts per
email-and-IP in 15 minutes.
It is deliberately process-local and must be replaced before multiple API replicas or a
public trusted-proxy deployment.

## Health endpoint

`GET /health` returns:

```json
{
  "status": "ok",
  "service": "freecoinalert-api"
}
```

It reports only that the API process is running. It does not indicate readiness for a
database, market-data ingestion, alert evaluation, or Telegram delivery.

## One-Time Price Alert Persistence

Issue #29 provides database-only persistence for one-time price-cross alerts. It stores exact decimal
targets and immutable supported-market snapshots, durable `below`/`equal`/`above` crossing state,
terminal lifecycle timestamps, and one immutable deduplicated trigger event per alert. No alert HTTP
endpoint, Binance stream, evaluator, notification-outbox write, or Telegram message behavior is part
of this issue. The migration is `20260730_0005`; it was generated but not applied.

## One-Time Price Alert API

Issue #30 adds authenticated `POST /alerts/price`, `GET /alerts`, `GET /alerts/{alert_id}`, and
`DELETE /alerts/{alert_id}` endpoints. Creation and deletion require `X-CSRF-Token`; creation also
requires a UUID `Idempotency-Key`, a connected Telegram destination, a fresh approved market, and an exact
plain decimal target that satisfies the catalog bounds and tick. Each user may have 20 active alerts.
Responses are safe, use `Cache-Control: no-store`, and list owned non-deleted alerts with opaque cursors.
The first accepted market event initializes rather than triggers the alert. This issue adds no current-price
lookup, Binance stream, evaluator, alert-event/outbox write, or Telegram message behavior. Creates are limited
to 10 per user and 30 per direct IP, and deletes to 30 per user, per 15 minutes; limits are process-local.

## Centralized live-price stream

Issue #31 adds `uv run python -m freecoinalert_api.market_data.stream`, a separately runnable public Binance Spot aggregate-trade process. It first refreshes the controlled catalog and then connects one combined stream for ready supported symbols only. It normalizes valid aggregate trades to exact-decimal internal events, rejects malformed, stale, future, duplicate, unsupported, and out-of-order events, and records throttled latest operational state in `market_symbol_states`. It uses a PostgreSQL singleton advisory lock, a bounded internal queue, and reconnect backoff; it does not evaluate alerts, create events or outbox jobs, expose a current-price endpoint, or store trade history.

The stream uses the public `BINANCE_SPOT_WS_BASE_URL` (default `wss://stream.binance.com:9443`), `MARKET_EVENT_MAX_AGE_SECONDS` (10), `MARKET_EVENT_FUTURE_TOLERANCE_SECONDS` (2), `MARKET_CATALOG_REFRESH_SECONDS` (21600), `MARKET_STATE_WRITE_INTERVAL_SECONDS` (1), and `MARKET_STREAM_RECONNECT_MAX_SECONDS` (30) settings. Normal API startup does not contact Binance.

## Price-alert evaluator

The market stream evaluates one-time price crossings after recording each validated `PriceEvent`. It maintains an
active-alert registry, persists initialization and side changes, and atomically creates the immutable trigger,
terminal alert state, and `telegram_price_alert` outbox job. The notification worker formats the immutable payload
as plain UTC text and keeps delivery state separate from the alert lifecycle. Alert reads expose only a safe
market-data status and delivery summary.
