# FreeCoinAlert API

The API is the Python and FastAPI foundation for FreeCoinAlert. It includes the initial
user and authentication-session persistence layer, but exposes only an unauthenticated
process-health endpoint. Registration, login, cookies, authorization, alerts, market
data, Telegram delivery, and background work are not implemented.

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
`src/freecoinalert_api/api/router.py` composes routes, keeping future feature routes
outside the application entry point. `core/config.py` reads `DATABASE_URL`, while `db/`
owns typed SQLAlchemy models, asynchronous sessions, repositories, and Alembic
migrations. The only current route is `GET /health`.

## Environment rules

Keep component-specific variables in `.env` files that are not committed. Use
`.env.example` only for safe, consumed variable names and comments. The API consumes
`DATABASE_URL`; it must contain no production credentials in committed files.

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
