# Contributing to FreeCoinAlert

## Prerequisites

Use Docker with Docker Compose v2, Node.js `24.18.0` LTS, and pnpm `11.4.0`. The required Node.js version is recorded in [`.node-version`](.node-version), and the root package manifest pins pnpm.

For the integrated local stack, copy `.env.example` to `.env` and run `pnpm dev`. The Compose stack starts the web application, API, and local PostgreSQL server. `pnpm dev:down` stops the stack while preserving local data; `pnpm dev:reset` permanently removes the PostgreSQL volume and its contents.

## Install dependencies

```bash
pnpm install
```

## Root commands

```bash
pnpm format
pnpm format:check
pnpm verify
```

`format` formats the root workspace manifest files. `format:check` checks those files without changing them. `verify` currently runs the root formatting check; later component issues will extend it while preserving its name.

Do not add placeholder `lint` or `typecheck` commands. Issue #5 owns frontend linting and TypeScript checking, while Issue #6 owns backend linting, formatting, and Python static checking.

## Repository boundaries

- `apps/` contains deployable browser and API applications.
- `services/` contains separately runnable background processes.
- `packages/` contains reusable code that is not independently deployed.
- `packages/shared/` is reserved for concrete shared contracts when first required.

Use direct component commands only when intentionally working outside the integrated stack: `pnpm dev:web` starts the frontend and `pnpm dev:api` starts the API after its uv environment is synchronized. `pnpm dev` is the normal integrated local-startup path.

## Environment files

Shared variables belong in the root [`.env.example`](.env.example) only when more than one application or service consumes them. Component-specific examples belong in `apps/<component>/.env.example` or `services/<component>/.env.example`.

Never commit real credentials or secrets. Local `.env` files and local variants are ignored; every `.env.example` remains tracked.

## Workflow

Read [`AGENTS.md`](AGENTS.md) and the relevant documentation before making changes. All implementation work must be linked to a GitHub Issue with an explicitly approved solution comment. Keep changes scoped to that approval and update the required documentation in the same change.
