# US-0011: Run the Complete User E2E Suite with One Command

## Status

Approved

## User Story

As a FreeCoinAlert developer, I want one command to start an isolated application environment and test every user-facing route and interaction, so that I can verify the complete MVP without manually starting services, preparing data, contacting real providers, or cleaning up test resources.

## Primary Command

```bash
pnpm e2e
```

The command must own the complete lifecycle:

1. Validate the local E2E prerequisites and safety boundaries.
2. Remove stale resources from the dedicated E2E Compose project.
3. Start an isolated PostgreSQL database and deterministic external-provider simulator.
4. Run database migrations and deterministic E2E fixture preparation.
5. Start the real API, web application, market process, Telegram processes, notification workers, signal dispatcher, SSE behavior, and historical-analysis worker.
6. Wait for required initialization, completion, and health states.
7. Run the complete Playwright browser suite.
8. Save safe failure artifacts and bounded service logs.
9. Stop the E2E project and remove its volumes after success, failure, or interruption.
10. Return a non-zero exit status when startup, a required service, or any test fails.

No manually running local stack may be required.

## Context

FreeCoinAlert now provides a complete redesigned MVP browser application with:

- Registration, sign-in, session restoration, and sign-out
- Responsive dashboard navigation and overview
- Light, dark, and system themes
- Private Telegram linking and test delivery
- One-time price alerts
- Fixed preset subscriptions
- Telegram delivery preferences for preset signals
- Historical and live signal history through SSE
- Browser signal sound
- Historical fixed-preset analysis
- Persisted reports, hypothetical trades, and equity data
- Responsive and accessible dialogs, drawers, tabs, forms, cards, tables, and charts

The repository also provides one-command local startup, but that developer environment uses persistent local state and may contact real Binance or Telegram. A complete E2E suite requires stronger isolation and deterministic provider behavior.

## Approved Test Architecture

Use Playwright for browser E2E testing.

Approved initial browser scope:

- Chromium desktop for the complete functional suite
- Chromium mobile emulation for selected responsive and mobile-navigation journeys
- One Playwright worker initially to keep shared provider and database scenarios deterministic

The E2E suite must exercise the real:

- Browser application
- API
- Authentication and CSRF flow
- PostgreSQL database
- Migrations
- Market-data process
- Alert evaluation
- Telegram update processor
- Notification worker
- Preset-signal dispatcher
- Historical and live signal feed
- SSE replay, recovery, and invalidation
- Historical-analysis worker
- Report persistence and reads

Only external providers may be simulated.

## Isolation Requirements

The E2E environment must use a dedicated:

- Compose project name
- PostgreSQL database and credentials
- Docker network
- Named volumes
- Local ports
- Environment file or committed test configuration
- Provider simulator
- Artifact directory

It must not read, write, reset, stop, or remove the normal local-development database, containers, networks, or volumes.

Starting `pnpm e2e` while the developer stack exists must not corrupt or reuse that stack.

The E2E command must remove only resources belonging to its own fixed project identity.

## External-Provider Safety

The E2E suite must never:

- Contact real Binance REST endpoints
- Connect to real Binance WebSocket endpoints
- Poll the real Telegram Bot API
- Send real Telegram messages
- Require a real Telegram bot token
- Use a developer's private provider credentials

The E2E provider simulator must supply the minimum deterministic contracts needed for the implemented application:

### Binance simulator

- Supported-market metadata
- Historical klines
- Live price events
- Closed one-minute candle events
- Market unavailable state
- Disconnect and reconnect behavior
- Deterministic event ordering and timestamps

### Telegram simulator

- Bot identity
- Polling updates
- `/start` linking updates
- Successful `sendMessage`
- Temporary failure
- Permanent failure
- Rate limiting
- Uncertain delivery outcome

Provider base URLs must remain configurable while production defaults remain unchanged.

The E2E runner must reject configuration that resolves to known real-provider hosts.

## Deterministic Data Requirements

E2E fixture setup must be deterministic and must not download production market history.

Provide bounded scenarios for:

- Empty new account
- Populated dashboard account
- Connected and disconnected Telegram states
- Active and terminal price alerts
- Alert crossing and delivery
- Active and disabled preset subscriptions
- Telegram delivery ready, disconnected, and degraded states
- Signal history pagination
- Live signal occurrence
- Signal replay and invalidation
- Complete historical-analysis report
- Zero-trade historical-analysis report
- Undefined metric outcomes
- Trade pagination
- Equity pagination
- Queued, running, succeeded, failed, and cancelled analysis runs

Users should be created through normal browser/API behavior where that user journey is under test. Additional fixture users may be prepared through approved test-only setup for isolated feature specifications.

Test-only fixture or scenario controls must not become public normal-runtime application endpoints.

## Authentication Coverage

Cover:

- Unauthenticated route protection
- Sign-up validation
- Successful registration
- Existing-email response
- Successful sign in
- Incorrect credentials
- Session restoration after reload
- Sign out
- Expired or revoked session
- Redirect after authentication loss
- Clearing owner-sensitive page state after authentication loss

The tests must use the real session cookie and server-issued CSRF token.

## Dashboard Coverage

Cover:

- Desktop sidebar navigation
- Sidebar collapse and expansion
- Active-route indication
- Breadcrumbs and page titles
- User menu
- Theme selection
- Theme persistence for the approved non-sensitive preference
- Skip navigation
- Mobile navigation drawer
- Empty overview state
- Populated overview state
- Partial-unavailable and safe-error states
- Primary actions to alerts and presets

Overview assertions must use only the existing exact application semantics and must not invent provider health or delivery history.

## Telegram Coverage

Cover the complete user flow:

```text
Disconnected
→ Create connection link
→ Simulator supplies the /start update
→ Telegram poller processes the update
→ Browser refreshes connection state
→ Connected
→ Queue test notification
→ Notification worker calls the simulator
→ Notification becomes sent
→ Disconnect with confirmation
```

Also cover:

- Linking state
- Expired link
- New link after expiry
- Connection refresh
- Degraded state
- Test notification pending
- Test notification failed
- Refreshing pending notification state
- Disconnect cancellation
- Reconnect path
- Owner-visible alert and subscription usage summaries

## Price-Alert Coverage

Cover:

- Telegram-required restriction when disconnected
- Market selection
- Crossing direction selection
- Empty and malformed target validation
- Market range and tick validation
- Alert creation
- Initial live-price readiness
- Active monitoring
- Provider-simulated crossing
- Triggered state
- Queued, sending, retrying, sent, failed, and uncertain notification states where visible
- Stale market state
- Disconnected market state
- Unavailable market state
- Lifecycle filters
- Pagination
- Refresh behavior
- Delete confirmation
- Cancelled deletion
- Successful deletion
- Terminal alert that cannot be deleted
- Authentication expiry during the workflow

The browser must call the real FreeCoinAlert API. Tests must not mock or intercept application API responses.

## Preset-Signal Coverage

Cover:

- Market filter
- Timeframe filter
- Subscription-status filter
- Subscribe action
- Disable confirmation and cancellation
- Telegram-delivery enable confirmation
- Telegram-delivery disable action
- Disconnected, linking, and degraded Telegram readiness
- Technical-details presentation
- Presets and Signal History tabs
- History filtering
- History pagination
- Browser sound activation
- Browser sound mute
- Live SSE signal arrival
- SSE reconnect and replay
- Reset recovery
- Duplicate-event prevention
- Signal invalidation
- Empty and unavailable states
- Session expiry while streaming

The signal stream, dispatcher, database, and workers remain real. External provider events originate from the simulator.

## Historical-Analysis Coverage

Cover:

- Market selection
- Fixed preset selection
- UTC start and end dates
- Completed-day validation
- Minimum-range validation
- Maximum-range validation
- Server-controlled assumption disclosure
- Review step
- Return from review to configuration
- Confirm and queue analysis
- Queued state
- Running state
- Reload while active
- Successful completion
- Queued-run cancellation
- Running cancellation request
- Terminal failure
- Safe error state
- Idempotent submission behavior
- Session expiry during the flow

Report coverage must include:

- Summary metrics
- Positive, negative, and zero values
- Zero-trade result
- Undefined win rate
- Undefined profit factor
- Equity chart
- Accessible equity table
- Trade pagination
- Equity pagination
- Coverage data
- Dataset, preset, calculation, engine, assumption, and simulation versions
- Complete fingerprints
- UTC timestamps
- Exact decimal strings
- Safety and synthetic-short disclosures

The browser must not recalculate strategy or performance semantics.

## Responsive Coverage

The mobile subset must cover the most important interaction patterns:

- Sign-in and registration
- Dashboard navigation drawer
- Alert creation dialog or drawer
- Alert lifecycle cards or tables
- Preset filters and details
- Telegram linking and connection controls
- Historical-analysis configuration
- Historical-analysis report tabs
- Responsive tables and chart containers
- Confirmation dialogs and destructive actions

No major page may create page-level horizontal overflow. Bounded table and chart containers may scroll internally where designed.

## Accessibility Coverage

Use `@axe-core/playwright` for approved stable page states.

Explicitly test:

- Keyboard-reachable controls
- Logical focus order
- Visible focus
- Skip navigation
- Correct landmarks and headings
- Accessible labels and descriptions
- Error association
- `aria-live` feedback
- Dialog and drawer focus trapping
- Focus return after close
- Tabs and menu keyboard behavior
- Status meaning not conveyed through colour alone
- Accessible chart alternatives
- Mobile drawer accessibility

Serious automated accessibility violations must fail the suite unless an exact exclusion is separately documented and approved.

## Selector and Waiting Rules

Prefer selectors in this order:

1. Accessible role and name
2. Associated label
3. Visible text where stable
4. Approved `data-testid` only when no reliable semantic selector exists

Do not use selectors based on generated CSS classes, DOM positions, or implementation-only structure.

Wait for visible business states such as:

- `Telegram connected`
- `Monitoring`
- `Triggered`
- `Signal stream live`
- `Analysis succeeded`
- `Notification sent`

Do not use arbitrary sleep-based waits.

## Failure Artifacts

Retain safe artifacts under a Git-ignored host directory such as:

```text
artifacts/e2e/
├── playwright-report/
├── test-results/
├── screenshots/
├── traces/
├── videos/
└── compose-logs/
```

Policy:

- Screenshot on failure
- Trace on failure or approved retry
- Video only on failure
- Bounded relevant service logs on startup or test failure
- No passwords, cookies, CSRF tokens, Telegram tokens, provider credentials, or raw private identifiers in artifacts

## Coverage Governance

Maintain a coverage document mapping:

- Browser route
- User-visible action
- Confirmation path
- Important visible states
- Desktop or mobile scope
- Playwright specification file

Intentionally excluded combinatorial cases must be listed separately from uncovered user paths.

The suite is not complete while a current route or user-triggered action is missing from the map.

## Out of Scope

- Real provider verification
- Production deployment verification
- Load or performance testing
- Trading or portfolio workflows
- Full Chrome, Firefox, and WebKit matrix
- Full visual-regression snapshot approval
- Unit, component, or API-only test strategy
- CI scheduling or merge-gate policy
- New product behavior added only to simplify tests

## Acceptance Criteria

- [ ] `pnpm e2e` is the only command required to start, test, collect artifacts, and destroy the isolated E2E environment.
- [ ] The normal developer stack and database are never reused or modified.
- [ ] No real Binance or Telegram endpoint is contacted.
- [ ] The real browser, API, PostgreSQL, migrations, workers, SSE, and historical-analysis worker are exercised.
- [ ] Every current user-facing route and user-triggered action is represented in the coverage map.
- [ ] Critical loading, empty, success, pending, degraded, stale, unavailable, failure, cancellation, recovery, and authentication-expiry states are covered.
- [ ] Desktop Chromium covers the full functional suite and the approved Chromium mobile subset covers responsive paths.
- [ ] Tests use semantic selectors, visible business-state waits, and no arbitrary sleeps.
- [ ] Failure artifacts are retained safely.
- [ ] Teardown removes the E2E project and volumes after success, failure, or interruption.
- [ ] The command returns non-zero for startup, service, accessibility, or browser-test failures.
- [ ] Current testing, product, architecture, security, accessibility, operations, observability, README, concerns, and continuity documentation remain synchronized.

## Implementation Issues

- #112 — Add isolated full-stack environment and provider simulator
- #113 — Add Playwright framework and one-command full-suite runner
- #114 — Cover authentication, dashboard, Telegram, alerts, and preset signals
- #115 — Cover historical analysis, recovery, responsive, and accessibility paths

Implementation order:

```text
#112 → #113 → #114 → #115
```

Each issue requires an explicitly approved technical solution comment before implementation.

## Verification Boundary

Planning approval does not authorize package installation, Playwright browser installation, Compose startup, migrations, fixture seeding, tests, builds, browser interaction, HTTP requests, providers, workers, linting, formatting checks, type checks, accessibility scanners, or other verification commands. Those remain subject to explicit maintainer direction.