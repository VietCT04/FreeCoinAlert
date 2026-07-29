# FreeCoinAlert API

The API is the Python and FastAPI foundation for FreeCoinAlert. It includes user and
authentication-session persistence, unauthenticated process health, and account
registration, sign-in, current-user lookup, and logout. Frontend authentication,
alerts, market data, Telegram delivery, and background work are not implemented.

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
`api/routes/auth.py` provides registration, sign-in, current-user lookup, and logout,
while `auth/` contains focused email, origin, password, rate-limit, session, and
authenticated-principal helpers. `core/config.py` reads
database and browser-authentication settings; `db/` owns typed SQLAlchemy models,
asynchronous sessions, repositories, and Alembic migrations.

## Environment rules

Keep component-specific variables in `.env` files that are not committed. Use
`.env.example` only for safe, consumed variable names and comments. The API consumes
`DATABASE_URL`, `WEB_ORIGIN`, `SESSION_COOKIE_SECURE`, and `SESSION_TTL_SECONDS`; they
must contain no production credentials in committed files. The local browser defaults
are `http://localhost:3000`, `false`, and seven days (`604800`) respectively.

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
