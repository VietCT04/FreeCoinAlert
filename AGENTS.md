# AGENTS.md

## Project Overview

FreeCoinAlert is a cryptocurrency market-alert platform.

Users connect Telegram to the web application, subscribe to platform-provided signal templates, or create validated custom alert rules. The system consumes real-time Binance market data, evaluates alert conditions, and sends Telegram notifications.

The platform also builds an internal historical candle database. A later analysis service will use stored data and the same strategy engine as live alerts rather than querying Binance separately for every customer calculation.

The system must protect users and platform reliability by preventing:

- Missed alerts caused by avoidable ingestion or processing failures.
- Duplicate alerts caused by retries, reconnects, repeated candles, or restarts.
- Unauthorized access to another user's alerts, Telegram connection, history, or results.
- Unsafe execution of customer-provided code.
- Different indicator behavior between live and historical evaluation.
- Look-ahead bias or misleading historical-performance claims.
- Binance rate-limit violations caused by uncoordinated API usage.
- Exposure of Telegram tokens, database credentials, authentication secrets, or other sensitive values.

FreeCoinAlert provides informational alerts only.

The initial product must not:

- Execute trades.
- Hold customer funds.
- Request or store customer Binance API keys.
- Promise profit or guaranteed alert delivery.
- Present historical simulation as financial advice.

This repository is a monorepo.

## Repository Structure

- `apps/web`: frontend application
- `apps/api`: backend API
- `services/market-data`: Binance WebSocket ingestion, candle persistence, aggregation, reconciliation, and historical backfill
- `services/notifications`: notification outbox processing and Telegram delivery
- `packages/shared`: shared types, DTOs, enums, validation schemas, constants, and API contracts
- `packages/strategy-core`: shared candle aggregation, indicators, conditions, validation, and evaluation used by live alerts and future historical analysis
- `docs`: product, architecture, API, database, security, market-data, alert, Telegram, strategy, backtesting, operations, observability, concern, continuity, and user-story documentation

Do not create all folders in advance. Introduce structure only when an approved GitHub Issue requires it.

## Mandatory Working Rule

Before making changes, read the relevant docs.

After making changes, update the relevant docs.

Code and docs must stay synchronized.

If a change affects behavior, API, database, security, market-data ingestion, candle aggregation, alert evaluation, Telegram linking, notification delivery, strategy definitions, historical analysis, deployment, or monitoring, documentation must be updated in the same change.

## Minimal Change Rule

Make the smallest correct change possible.

Do not refactor unrelated code.

Do not rename files, move folders, rewrite modules, split services, or introduce new patterns unless the GitHub Issue explicitly requires it.

Prefer surgical changes over broad redesigns.

When modifying existing code:

1. Understand the current pattern.
2. Follow the existing style.
3. Change only what is necessary.
4. Avoid touching unrelated files.
5. Avoid dependency additions unless clearly justified.
6. Avoid distributed infrastructure before measurements demonstrate a need.

Do not introduce Redis, Celery, Kafka, Kubernetes, or additional microservices merely because they may be useful later.

## Code Formatting Rules

Code must be readable and match surrounding repository conventions. Do not compress implementation code to reduce line count.

- Use one field, statement, annotation, method declaration, and assignment per logical line.
- Use explicit imports rather than wildcard imports unless the module already establishes another convention.
- Wrap long signatures, calls, object construction, and boolean conditions with consistent indentation.
- Extract compound validation, candle processing, alert evaluation, response construction, and lifecycle transitions into clearly named functions when a line becomes difficult to scan.
- Keep whitespace, braces, accessors, and control flow consistent with nearby files.
- Do not place multiple declarations, assignments, methods, or branches on one line.
- Preserve normal formatting even when verification commands are deferred.
- Use domain names such as `closed_candle`, `alert_event`, `notification_outbox`, and `strategy_version` rather than vague names such as `data` or `item`.

## Documentation Update Rules

Update these docs when relevant:

| Change Type | Required Docs |
|---|---|
| Product behavior or scope | `docs/PRODUCT.md` |
| Components, boundaries, or data flow | `docs/ARCHITECTURE.md` |
| API endpoint, request, response, error, or authorization | `docs/API.md` |
| Database schema, status, index, partition, or retention | `docs/DATABASE.md` |
| Security, authentication, permissions, secrets, or abuse controls | `docs/SECURITY.md` |
| Binance ingestion, aggregation, reconciliation, or backfill | `docs/MARKET_DATA.md` |
| Alert lifecycle, evaluation, cooldown, state, or deduplication | `docs/ALERTS.md` |
| Telegram linking, webhook, destination, or delivery | `docs/TELEGRAM.md` |
| Indicator, custom rule, template, or version behavior | `docs/STRATEGIES.md` |
| Historical simulation or performance calculation | `docs/BACKTESTING.md` |
| Deployment, configuration, backup, or recovery | `docs/OPERATIONS.md` |
| Logs, metrics, health, freshness, or incident signals | `docs/OBSERVABILITY.md` |
| User story or product requirement | `docs/user-stories/*.md` |
| Unresolved risk or uncertainty | `docs/CONCERNS.md` |
| Work handoff and project state | `docs/CONTINUITY.md` |

If no documentation update is needed, explicitly mention why in the final response.

## GitHub Issues Workflow

All implementation work should be linked to a GitHub Issue.

Open issues represent unresolved work. Closed issues represent completed work.

Do not create local ticket files under `docs/tickets/`. Use GitHub Issues.

User stories may describe broad behavior, but implementation issues should be small slices. Prefer several focused issues over one large issue when work spans authentication, Telegram, database, market data, alerts, frontend, security, operations, or historical analysis.

Each implementation issue should normally have:

- One primary outcome.
- One main affected area.
- Acceptance criteria that can be verified independently.
- Clear out-of-scope work.
- Known concerns or open decisions.

Before resolving an issue, write a proposal in the GitHub Issue comments and wait for user approval.

Use the issue thread as the approval and revision loop. If the user comments on the proposal, post a revised proposal and repeat until approved.

If GitHub is unavailable, write the proposal in the conversation and mirror the approved proposal to the issue when access is restored.

A proposal should summarize:

- Intended scope
- Files to update
- API or schema decisions
- Market-data or alert-lifecycle decisions
- Security and reliability implications
- Open questions
- Verification approach
- What will be reported back to GitHub

After approval, implement the smallest correct change and update `docs/CONTINUITY.md`.

Before posting after approval, read existing issue comments. Do not duplicate an approved proposal already present. Add completion notes in the linked pull request or post only genuinely new information.

When completing an issue:

1. Implement the smallest correct change.
2. Update affected docs.
3. Add unresolved risks to `docs/CONCERNS.md`.
4. Update `docs/CONTINUITY.md`.
5. Add completion notes to the issue or linked pull request.
6. Close the issue only when work is complete and verified.

## Issue Creation Rule

When a task comes from a user story, create one or more focused GitHub Issues.

User stories live in:

```text
docs/user-stories/
```

Each issue should include:

```md
# Short Title

## Source

User Story: `docs/user-stories/US-0001-example.md`

## Context

Explain why this task exists.

## Goal

Explain the desired outcome.

## Scope

Describe the narrow implementation slice.

## Out of Scope

List related work for separate issues.

## Concerns

List risks, uncertainties, or decisions requiring review.
```

## User Story Workflow

User stories describe product behavior from a user's perspective and are the source for implementation issues.

Use stories for:

- Account and authentication flows
- Telegram connection and disconnection
- Browsing and subscribing to signal templates
- Creating, editing, pausing, resuming, and deleting alerts
- Notification preferences and alert history
- Historical strategy analysis
- Administrative management of supported markets and templates

Filename format:

```text
US-0001-short-title.md
```

Template:

```md
# US-0001: Short Title

## User Story

As a [user type], I want [goal], so that [benefit].

## Context

Explain why this behavior matters.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Sensitive actions are enforced server-side where relevant
- [ ] External-event behavior is idempotent where relevant
- [ ] Relevant docs are updated

## Risks

## Follow-up Issues

- GitHub Issue: `#123`
```

## CONCERNS.md Rule

Use `docs/CONCERNS.md` for unresolved risks, assumptions, and questions.

Add a concern when:

- A requirement is ambiguous.
- A security or authorization risk exists.
- Binance behavior or rate-limit handling is uncertain.
- Candle continuity, retention, or timestamp alignment is unresolved.
- Alert deduplication or cooldown behavior is unclear.
- Indicator output cannot be matched between live and historical evaluation.
- Telegram linking or delivery has an unresolved edge case.
- A database migration, partition, or retention change may be risky.
- Historical analysis assumptions may mislead users.
- A temporary workaround is used.
- A meaningful test cannot be added or run.
- A dependency, infrastructure, or provider choice needs review.

Do not hide important uncertainty only in code comments.

## CONTINUITY.md Rule

Update `docs/CONTINUITY.md` after every meaningful change.

It must contain:

- Current project state
- Latest completed work with date, issue, summary, and files
- Active issue, goal, and blocker
- Important user stories
- Known concerns
- Market-data state
- Next recommended steps

## Database Rules

Before changing database structure:

1. Read `docs/DATABASE.md`.
2. Inspect existing models, migrations, enums, indexes, partitions, and relationships.
3. Make the smallest schema change.
4. Add or update migrations.
5. Update `docs/DATABASE.md`.
6. Update shared types if needed.
7. Update API docs when behavior changes.
8. Consider idempotency, retention, query patterns, backup, and rollback.

Never change alert, candle, strategy, delivery, or connection states without checking all affected transitions.

Candle uniqueness must be equivalent to:

```text
(exchange, market_type, symbol, open_time)
```

Use UTC timestamps. Use idempotent writes. Never overwrite a confirmed closed candle with an unfinished candle.

## API Rules

Before changing API behavior:

1. Read `docs/API.md`.
2. Check request, response, and shared schemas.
3. Validate all input server-side.
4. Enforce ownership and authorization server-side.
5. Update frontend consumers.
6. Update `docs/API.md`.

Do not invent a new endpoint when an existing endpoint can be safely extended.

Do not change response shapes without updating all consumers.

Do not expose internal Binance state, Telegram credentials, raw provider errors, or another user's data.

## Frontend Rules

- Use shared API types and validation models.
- Do not duplicate backend DTOs manually.
- Handle loading, empty, success, disabled, and error states.
- Do not rely on frontend-only ownership or security checks.
- Clearly distinguish real-time price alerts from candle-close indicator alerts.
- Show symbol, market, timeframe, evaluation mode, cooldown, and destination before activation.
- Do not claim guaranteed alert delivery.
- Do not show historical performance without assumptions, date range, sample size, fees, slippage, and strategy version.
- Keep components focused and readable.

## Backend Rules

- Validate all user and provider input.
- Enforce authorization server-side.
- Keep business logic outside thin route layers.
- Use explicit alert, connection, and notification transitions.
- Record important lifecycle events.
- Make externally triggered processing idempotent.
- Never trust client-provided ownership or trigger state.
- Never execute arbitrary customer Python, JavaScript, SQL, shell, or templates.
- Bound rule depth, condition count, parameter ranges, and computational complexity.
- Centralize exchange clients and rate limiting.
- Do not block real-time ingestion with historical work.

## Market-Data Rules

Before changing market-data behavior, read `docs/MARKET_DATA.md`.

Required rules:

- Binance WebSocket is primary for live prices and one-minute kline events.
- Persist one-minute candles only when confirmed closed.
- Daily processing reconciles missing ranges; it is not the sole ingestion path.
- Historical backfill is isolated from real-time alert processing.
- Do not create a Binance connection per user.
- Share subscriptions by exchange, market, symbol, and stream type.
- Reconnect with bounded exponential backoff and detect gaps.
- Respect request weights and retry guidance.
- Store and aggregate timestamps in UTC.
- Make ingestion idempotent.
- Do not silently synthesize missing candles.

## Candle Aggregation Rules

- Closed one-minute candles are canonical unless an approved issue changes this.
- Derive larger timeframes internally using UTC boundaries.
- Do not evaluate candle-close strategies from incomplete aggregates.
- Live and historical aggregation must use the same implementation.
- Define missing-candle, precision, and rounding behavior explicitly.

## Alert Evaluation Rules

### Price Alerts

- May evaluate from real-time ticker or trade events.
- Must track state so a crossing does not repeat while price remains on the same side.
- Must define restart and reconnect behavior.

### Indicator Alerts

- Evaluate on closed candles by default.
- Intrabar behavior requires an explicit issue and user-facing semantics.
- Use the shared strategy core.
- Persist state required for crossovers and deduplication.
- Share indicator calculations where practical.

Every trigger must be reproducible from the rule version, market, symbol, timeframe, event or candle time, relevant values, and evaluation mode.

## Strategy Rules

- Use a constrained, validated rule format.
- Never execute arbitrary customer code.
- Validate indicators, operators, parameters, timeframes, nesting, and complexity.
- Version platform templates.
- Keep subscriptions pinned to a template version unless users upgrade.
- Do not silently change a published template's meaning.
- Live and historical evaluation must use the same strategy-core implementation.

## Notification Rules

Use a durable outbox or job table.

The alert transaction should create the alert event and notification job atomically.

The worker should claim jobs safely, send Telegram messages, record outcome, retry temporary failures with bounded backoff, and mark permanent failures.

Successful evaluation is not the same as successful delivery.

Add uniqueness or idempotency rules preventing duplicate messages for the same alert event and destination.

## Telegram Rules

Before changing Telegram behavior, read `docs/TELEGRAM.md`.

Required rules:

- Connect through a bot deep link.
- Use securely random, short-lived, single-use tokens.
- Do not expose internal user IDs in link tokens.
- Process Telegram updates idempotently.
- Enforce destination ownership.
- Never commit the bot token or webhook secret.
- Validate webhook authenticity when webhooks are used.
- Store the minimum Telegram identity data required.
- Define behavior when the bot is blocked or a chat becomes unavailable.

## Historical Analysis Rules

Backtesting is a later phase, but current work must not make it inconsistent.

Before changing historical analysis, read `docs/BACKTESTING.md`.

Required rules:

- Use stored platform data after coverage is validated.
- Do not call Binance separately per customer request.
- A signal alone does not have a meaningful win rate.
- Define entry, execution, exit, stop loss, take profit, duration, fees, slippage, and sizing.
- Prevent look-ahead bias.
- Include date range, sample size, strategy version, data source, and assumptions in results.
- Do not optimize or advertise only win rate.
- Keep historical jobs isolated from live processing.

## Testing Rules

Add or update tests when practical, especially for:

- Authorization and ownership
- Telegram token expiry and single use
- Binance reconnect and gap detection
- Candle uniqueness and idempotency
- UTC aggregation
- Indicator calculations
- Crossover state
- Alert deduplication
- Notification retries
- Rule validation and template versioning
- Historical look-ahead prevention

No tests or verification commands need to be run after coding. Do not run backend or frontend test suites, migrations, or verification commands unless the maintainer explicitly requests a dedicated verification pass.

This applies equally to approved API, security, and Telegram connection work: implementation
does not require test, build, lint, type-check, formatting, migration, database, browser, or
manual API verification execution.

This no-verification instruction includes browser interaction and manual API checks for approved frontend work.

For approved database-persistence work, it also includes Alembic upgrade or downgrade
execution, database schema inspection, and transactional repository checks.

When an approved issue also excludes test files or testing dependencies, do not add them as part of implementation.

This also prohibits Docker builds, Compose startup, container health checks, HTTP requests, and database connection commands unless the maintainer explicitly requests that verification pass.

Agents may write or update tests when practical. Do not run lint, build, typecheck, migration validation, formatting, or other verification commands unless the maintainer explicitly requests a dedicated verification pass.

If the user approves PR- or CI-level review or says local tests are unnecessary, do not repeatedly attempt local tests. State clearly that they were not run by user direction.

If verification cannot run because of environment, toolchain, dependency, or external-service limitations, explain the reason and update `docs/CONCERNS.md` when the risk is meaningful.

Tests must use deterministic fixtures and mocked Binance and Telegram clients. Normal tests must not depend on live external services.

## Shared Package Rules

Use `packages/shared` for:

- DTOs
- Enums
- Validation schemas
- Constants
- API contract types
- Supported market and timeframe definitions when appropriate

Use `packages/strategy-core` for:

- Candle and aggregation models
- Indicators
- Conditions and rule models
- Crossovers
- Evaluation logic
- Strategy versions
- Deterministic live and historical behavior

Do not duplicate these across frontend, API, live processing, and historical analysis.

## Security Rules

- Never commit secrets.
- Never expose database URLs, Telegram bot tokens, authentication secrets, webhook secrets, or private keys.
- Never request customer exchange API keys in the alert-only MVP.
- Never execute arbitrary customer code.
- Validate and bound custom-rule complexity.
- Require admin authorization for admin endpoints.
- Users may access only their own alerts, connections, history, and results.
- Rate-limit authentication, linking, alert creation, test notifications, and expensive analysis.
- Do not include secrets or unnecessary personal data in logs.
- Protect internal worker endpoints.
- Make sensitive actions auditable.

## Reliability and Observability Rules

Track enough information to determine:

- Whether Binance connections are healthy and fresh
- The last closed candle stored for each supported symbol
- Known candle gaps and repair state
- Alert evaluation latency and failures
- Trigger and duplicate-prevention counts
- Notification backlog, retries, failures, and latency
- Database availability and storage growth

Use structured logs and avoid logging every market tick.

Health checks must distinguish API process health, market-data freshness, database health, alert-engine health, and notification health.

## Deployment and Portability Rules

- Use Docker and Docker Compose for local development when executable components are introduced.
- Keep configuration in environment variables.
- Do not hard-code provider-specific credentials or hostnames.
- Keep persistent data outside ephemeral containers.
- Document ports, volumes, environment variables, and health checks.
- Target `docker compose up` for local startup.
- Do not couple behavior to a specific hosting provider without an approved issue.
- Prefer a modular monolith and separate processes before independent microservices.

## Financial and Product Communication Rules

- Do not claim an indicator predicts future prices.
- Do not claim guaranteed profits, guaranteed delivery, or risk-free trading.
- Do not display win rate without assumptions and sample size.
- Clearly distinguish historical simulation from future performance.
- Clearly state candle-close versus intrabar evaluation.
- Store UTC internally and allow user-local display formatting.
