# FreeCoinAlert Web

The web application is the browser foundation for FreeCoinAlert. It uses Next.js,
TypeScript, the App Router, Tailwind CSS, and Server Components by default.

## Prerequisites

- Node.js `24.18.0`
- pnpm `11.4.0`

Install workspace dependencies from the repository root:

```bash
pnpm install
```

## Local Commands

Run these commands from the repository root:

```bash
pnpm dev:web
pnpm build:web
pnpm lint:web
pnpm typecheck:web
```

`pnpm dev:web` starts the local development server on [http://localhost:3000](http://localhost:3000).
`pnpm build:web` produces a production build, and `pnpm --filter @freecoinalert/web start` serves that build.

## Integrated Compose Startup

From the repository root, copy `.env.example` to `.env` and run `pnpm dev` to start the web application with the API and local PostgreSQL stack. The web container binds only to `127.0.0.1` on the configured `WEB_PORT` (default `3000`). Use `pnpm dev:down` to stop the stack or `pnpm dev:reset` to remove all local Compose volumes, including PostgreSQL data.

## Directory Purpose

- `src/app/` contains App Router routes, the root layout, and global styles.
- `public/` holds static assets when a future approved feature requires them.

## Environment Rules

- Browser-exposed variables require the `NEXT_PUBLIC_` prefix.
- Secrets must never use `NEXT_PUBLIC_`.
- Add variables only when they are consumed by implemented code.
- Shared variables belong in the repository root `.env.example`; web-only variables belong in `.env.example` here.

`NEXT_PUBLIC_API_BASE_URL` is required by the browser authentication client. It defaults to `http://localhost:8000` in the committed examples and is deliberately limited to the API origin, not a secret or session credential. The client uses credentialed browser `fetch` requests; it never reads or stores the HTTP-only session cookie.

## Telegram Connection UI

Authenticated users can request a one-time Telegram bot deep link, refresh their safe connection
state, queue a test notification, and disconnect with an inline confirmation. The frontend keeps
the deep link, test-notification idempotency key, connection state, and delivery status only in
React memory. It never reads the HTTP-only session cookie or stores Telegram identifiers or linking
tokens in browser storage.

While a link is active, connection status polls every two seconds for at most ten minutes and pauses
when the tab is hidden. Test-notification status follows the same bounded polling pattern for up to
one minute. A later maintainer-requested verification pass must exercise a configured bot before
claiming Telegram verification is complete.

## Current Limitations

The minimal registration, sign-in, session restoration, current-session sign-out, and Telegram
connection flow are implemented. Alert management, market charts, profile editing, deployment
configuration, a reusable design system, and dedicated authentication or Telegram verification
passes remain out of scope or incomplete.
