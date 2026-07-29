# FreeCoinAlert API

The API is the Python and FastAPI foundation for FreeCoinAlert. It includes user and
authentication-session persistence, unauthenticated process health, account
registration, sign-in, current-user lookup, logout, and authenticated Telegram link-token,
connection-state, and disconnect APIs. Frontend Telegram interaction, Telegram Bot API
integration, update processing, alerts, delivery, and background work are not implemented.

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
one-time token creation, link and disconnect transactions, and a bounded local limiter;
it creates no Telegram bot client, webhook, polling process, update parser, or confirmation.

## Environment rules

Keep component-specific variables in `.env` files that are not committed. Use
`.env.example` only for safe, consumed variable names and comments. The API consumes
`DATABASE_URL`, `WEB_ORIGIN`, `SESSION_COOKIE_SECURE`, `SESSION_TTL_SECONDS`,
`TELEGRAM_BOT_USERNAME`, and `TELEGRAM_LINK_TTL_SECONDS`; they
must contain no production credentials in committed files. The local browser defaults
are `http://localhost:3000`, `false`, and seven days (`604800`) respectively.

`TELEGRAM_BOT_USERNAME` is optional, public configuration with no leading `@` and only
Telegram username characters. If it is absent, link creation returns a safe `503` response.
`TELEGRAM_LINK_TTL_SECONDS` defaults to 600. Never add a bot token under this API boundary.

## Telegram connection endpoints

`POST /telegram/link-tokens` requires the HTTP-only session and `X-CSRF-Token`, returns a
one-time deep link plus `linking` expiry, and commits its SHA-256 token hash before returning.
The raw token appears only in that URL. `GET /telegram/connection` returns the current user's
safe status only. `DELETE /telegram/connection` requires CSRF, idempotently disconnects the
current saved destination, and revokes outstanding tokens. All connection responses use
`Cache-Control: no-store` and never expose chat IDs, Telegram user IDs, hashes, or raw tokens.

The local in-memory limiter permits five link requests per user and ten per direct client IP,
plus ten disconnect requests per user, in fifteen minutes. It is not sufficient for multiple
API replicas or an untrusted proxy deployment. No Telegram transport, `/start` processing,
confirmation, test notification, or frontend flow exists yet.

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
