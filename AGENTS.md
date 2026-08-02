# AGENTS.md

## Current Project Overview

FreeCoinAlert is an informational cryptocurrency market-alert platform. Signed-in users connect a private Telegram destination, manage one-time price-crossing alerts for a controlled Binance Spot catalogue, and can subscribe to fixed preset signals. The platform persists canonical closed candles and evaluates global preset-signal occurrences.

The product does not execute trades, hold customer funds, request or store customer exchange API keys, provide financial advice, promise profit, or guarantee delivery. Protect users and platform reliability from missed or duplicate alerts, unauthorized access, unsafe customer-provided code, inconsistent live and historical calculations, look-ahead bias, provider rate-limit violations, and sensitive-data exposure.

## Actual Repository and Runtime Structure

- `apps/web` is the Next.js browser application.
- `apps/api` is the FastAPI API and contains the separately runnable market stream, Telegram-update poller, notification worker, candle commands, and signal-backfill module entry points.
- `docs` contains authoritative current-state documentation, concerns, continuity, and user stories.
- `.github` contains contribution templates and workflow files when present.

Do not describe `services/market-data`, `services/notifications`, `packages/shared`, or `packages/strategy-core` as current runnable projects unless they exist and contain the described implementation. Future structure requires an approved issue and must not be presented as current beforehand. Do not create folders, services, packages, or runtime boundaries in advance.

## Mandatory Working Rules

- Work only within the target issue's approved solution.
- Read relevant current-state documentation before editing, inspect the current implementation, and make the smallest correct change.
- Keep code and current-state documentation synchronized in the same pull request.
- Preserve ownership, provider credential secrecy, exact-decimal market behavior, immutable event/version semantics, and separation of an occurrence from a delivery.
- Static repository and documentation inspection is implementation work, not a claim that runtime behavior was verified.

## Current-State Documentation Rules

### Source of Truth

- Merged code and authoritative domain documents describe the current system.
- GitHub issues, approved comments, user stories, and pull requests preserve requirements, scope, decisions, and history; they are not substitutes for current-state documentation.
- Before changing code, read `docs/README.md`, the authoritative documents for every affected domain, the target issue, and its approved solution.

### Same-Change and Replacement Rules

When a change modifies a current behavior or contract, update every affected authoritative document in the same pull request. This includes product or frontend behavior, HTTP contracts, schemas and lifecycle, security and ownership, provider or market-data behavior, alert or strategy semantics, Telegram or notification behavior, configuration and commands, runtime topology, maintenance and recovery, health and observability, and retention or deletion behavior.

Do not limit documentation updates to files named in an issue. Review related documents, README entry points, environment examples, and `docs/CONTINUITY.md` whenever they could become inaccurate.

When behavior changes:

- replace the old statement with the current rule;
- remove obsolete pending text;
- update affected examples, tables, diagrams, status values, commands, and configuration;
- remove contradictory or duplicate descriptions; and
- do not append an issue, pull-request, slice, or completion note instead of rewriting the explanation.

### History, Ownership, and Status Rules

Current-state domain documentation must not be organized as issue or pull-request chronology. GitHub holds implementation history. Approved user stories preserve requirements, not proof of current availability. Do not create a second completed-issue history under `docs/` unless separately approved; an approved ADR may preserve architectural reasoning when an ADR exists.

`docs/README.md` is the authoritative ownership map. One detailed contract has one owning document; other documents provide concise context and a relative link. READMEs are entry points, not copies of domain contracts.

Use these independent status dimensions:

```text
Availability: Implemented | Planned | Not supported | Unresolved
Verification: Verified | Unverified | Not applicable
```

- `Implemented` means present in merged `main`.
- `Verified` requires an explicit maintainer-requested verification pass.
- Approved or in-progress work is not Implemented.
- Do not use vague `done`, `working`, or `ready` wording when availability or verification is intended.

### README, Continuity, and Concerns Rules

README files contain only purpose, actual entry points, minimal setup, component commands, environment location, a concise current surface summary, and links to authoritative documentation. Do not duplicate full API, schema, strategy, provider, lifecycle, or security contracts, issue-completion diaries, or speculative roadmaps.

`docs/CONTINUITY.md` contains only current snapshot, active work, current blockers, verification status, next actions, and handoff constraints. Do not add latest-completed-work entries, completed-issue timelines, PR summaries, changed-file lists, full domain contracts, resolved decisions, or long roadmaps. Remove work from Active Work when it completes rather than moving it into a completed section.

`docs/CONCERNS.md` contains only genuinely unresolved current risks, limitations, assumptions, verification gaps, and decisions. Remove a concern when it is resolved; do not use concerns as a backlog or implementation diary.

## Documentation Ownership and Change Matrix

Review and update the owning document when affected; do not automatically touch every document in this table. See `docs/README.md` for detailed ownership.

| Change | Required authoritative review |
| --- | --- |
| User-visible capability, limit, or status | `PRODUCT.md` |
| Component, process, dependency, or data flow | `ARCHITECTURE.md` |
| Endpoint, request, response, error, auth, pagination, or rate limit | `API.md` |
| Table, column, relationship, constraint, index, transaction, retention, or migration | `DATABASE.md` |
| Authentication, authorization, secrets, trust, abuse, logging, or exposure | `SECURITY.md` |
| Binance, catalog, stream, candle, aggregation, repair, correction, freshness, or retention | `MARKET_DATA.md` |
| Alert/signal lifecycle, crossing, event, invalidation, deduplication, or delivery separation | `ALERTS.md` |
| Preset, formula, calculation version, warm-up, input, or outcome | `STRATEGIES.md` |
| Telegram linking, polling, destination, outbox, send, retry, or provider status | `TELEGRAM.md` |
| Command, environment setting, process, profile, maintenance, or recovery | `OPERATIONS.md` |
| Health, persistent status, structured log, measurement, redaction, or incident signal | `OBSERVABILITY.md` |
| Historical-analysis availability or semantic requirement | `BACKTESTING.md` |
| Unresolved current risk or decision | `CONCERNS.md` |
| Active work, blocker, verification summary, next action, or handoff constraint | `CONTINUITY.md` |

## Implementation Workflow

### Before Editing

1. Read this file and `docs/README.md`.
2. Read the target issue and approved solution.
3. Read all authoritative documents for affected domains.
4. Inspect current code and documentation; do not trust old issue summaries as implementation truth.
5. Identify the documents that own the changed contracts.

### During Editing

1. Make the smallest approved change.
2. Update owning documents in the same change.
3. Replace stale statements rather than appending history.
4. Add only genuinely unresolved concerns.
5. Keep README and continuity changes within their approved boundaries.

### Before Pull Request Completion

Perform a manual static documentation-consistency review:

1. Compare changed behavior, routes, schemas, models, migrations, settings, commands, statuses, logs, and frontend consumers with authoritative documents.
2. Search affected documentation for old values, stale pending language, duplicate contracts, and issue-completion wording.
3. Confirm Planned work is not described as Implemented.
4. Confirm implementation is not described as Verified without an explicit pass.
5. Confirm continuity contains current work only.
6. Record documentation impact in the pull-request description.

No command is required for this review.

## GitHub Issue and Approval Workflow

All implementation work is linked to a GitHub Issue. Open issues are unresolved work; closed issues are completed work. Do not create local ticket files under `docs/tickets/`.

Use focused implementation issues with one primary outcome, one main affected area, independently reviewable acceptance criteria, explicit out-of-scope work, and known concerns or decisions. Split broad user-story work into focused issues when it spans distinct domains.

Before implementation, propose the technical solution in the maintainer conversation when requested, obtain maintainer approval, then post the exact approved solution as a comment on the GitHub issue. Read existing issue comments before posting; do not duplicate an already-approved proposal. Implement only the approved scope.

The issue and pull request hold implementation history. Pull requests close their linked issue when complete; do not close an issue merely because documentation was proposed. The pull-request summary is the completion note. Update continuity only when its current-state sections change.

## Minimal Change Rule

Make the smallest correct change possible. Do not refactor unrelated code, rename or move unrelated files, split modules, add patterns, dependencies, infrastructure, or distributed services unless the approved issue requires them. Follow the established local pattern and avoid dependencies or infrastructure without clear justification. Do not introduce Redis, Celery, Kafka, Kubernetes, or additional microservices merely because they may be useful later.

## Code Formatting Rules

- Keep code readable and consistent with nearby code.
- Use one field, statement, annotation, method declaration, and assignment per logical line.
- Use explicit imports rather than wildcard imports unless the module establishes another convention.
- Wrap long signatures, calls, object construction, and boolean conditions consistently.
- Extract complex validation, candle processing, alert evaluation, response construction, and lifecycle transitions into clearly named functions when needed for readability.
- Use domain names such as `closed_candle`, `alert_event`, `notification_outbox`, and `strategy_version` rather than vague names.

## Domain Rules

### Database

Before changing database structure, read `docs/DATABASE.md`, inspect models, migrations, enums, indexes, and relationships, make the smallest schema change, update migrations and affected shared/API contracts, and consider idempotency, retention, query patterns, backup, and rollback. Never change alert, candle, strategy, delivery, or connection states without checking all affected transitions.

The logical current-candle identity is `(supported_market_id, timeframe, open_time)`.
Revision history is unique by `(supported_market_id, timeframe, open_time, revision)`.
Do not duplicate the exact schema here; `DATABASE.md` owns it. Store UTC timestamps, use idempotent writes, and never overwrite a confirmed closed candle with an unfinished candle.

### API

Before changing API behavior, read `docs/API.md`, inspect request, response, and shared schemas, validate all input server-side, enforce ownership and authorization server-side, update consumers, and update the HTTP contract. Do not expose internal provider state, credentials, raw provider errors, or another user's data.

### Frontend

Reuse existing frontend API types and update all consumers when an API contract changes. Do not introduce a shared package without an approved issue.

Show only fields applicable to the implemented flow. One-time price alerts show market, direction, target price, and Telegram readiness. Future preset interfaces display their server-provided timeframe and condition.

Handle loading, empty, success, disabled, and error states. Never rely on frontend-only ownership checks. Do not claim guaranteed delivery or display historical performance without assumptions and sample size.

### Backend

Validate user and provider input, enforce authorization server-side, and keep business logic outside thin route layers. Use explicit alert, connection, and notification transitions; record important lifecycle events; make externally triggered processing idempotent; and never trust client-supplied ownership or trigger state.

Never execute arbitrary customer code. Bound rule depth, condition count, parameter ranges, and computational complexity. Centralize exchange clients and rate limiting, and do not block real-time ingestion with historical work.

### Market Data and Candles

Before changing market-data behavior, read `docs/MARKET_DATA.md`. Binance WebSocket is primary for live prices and one-minute kline events. Persist one-minute candles only when confirmed closed; reconcile missing ranges separately from live ingestion; isolate historical backfill; share provider streams; reconnect with bounded backoff; detect gaps; respect request weights; store UTC; make ingestion idempotent; and never synthesize missing candles.

Closed one-minute candles are canonical. Derive larger timeframes using UTC boundaries, do not evaluate candle-close strategies from incomplete aggregates, and keep live and historical aggregation on the same implementation.

### Alerts and Strategies

Price alerts track crossing state to prevent repeat alerts while price remains on one side and define restart/reconnect behavior. Indicator alerts evaluate on closed candles by default; intrabar behavior requires an explicit issue and user-facing semantics. Every trigger must be reproducible from its rule version, market, symbol, timeframe, time, relevant values, and evaluation mode.

Use constrained, validated strategy rules. Version platform templates, keep subscriptions pinned unless a user upgrades, and do not silently change a published template's meaning. Live and historical evaluation must use the same strategy implementation.

### Telegram and Notifications

Before changing Telegram behavior, read `docs/TELEGRAM.md`. Link through a bot deep link using securely random, short-lived, single-use tokens. Process updates idempotently, enforce destination ownership, validate webhooks when used, store minimum identity data, and never commit tokens or secrets.

Use a durable outbox. Alert transactions create events and notification jobs atomically. Workers claim jobs safely, record outcomes, retry temporary failures with bounded backoff, mark permanent failures, and preserve idempotency that prevents duplicate messages. Successful evaluation is not successful delivery.

### Historical Analysis

Before changing historical analysis, read `docs/BACKTESTING.md`. Use stored platform data after coverage validation rather than querying Binance separately per customer calculation; define execution assumptions; prevent look-ahead bias; include date range, sample size, strategy version, data source, and assumptions; and isolate historical jobs from live processing. Do not optimize or advertise only win rate.

### Operations and Observability

Keep configuration in environment variables, persistent data outside ephemeral containers, and provider-specific credentials or hostnames out of code. Document ports, volumes, environment variables, health checks, process entry points, and recovery behavior in the owning operational document.

Use structured logs without logging every market tick. Preserve enough signals to distinguish API process health, market-data freshness, database health, alert-engine health, notification health, known candle gaps, alert-evaluation failures, and notification backlog or failures.

## Security and Sensitive Data

Never commit or expose database URLs, Telegram tokens, authentication secrets, webhook secrets, private keys, or unnecessary personal data. Do not request customer exchange API keys. Require server-side admin authorization, restrict users to their own data, rate-limit sensitive and expensive actions, keep sensitive actions auditable, and use structured logs without secrets.

Do not claim that an indicator predicts future prices, that alerts or investment outcomes are guaranteed, or that historical simulation is financial advice. Clearly distinguish candle-close from intrabar behavior and historical performance from future results.

## Verification Execution Rule

Do not run tests, builds, migrations, database commands, services, providers, browser interaction, linting, formatting checks, type checks, documentation generators, link checkers, or other verification commands unless the maintainer explicitly requests a dedicated verification pass.

Static code and documentation inspection is allowed. Never claim a verification result that was not produced. Pull requests must state exactly what was and was not run. Tests may be written when practical with deterministic fixtures and mocked providers, but are not run without that explicit request.

## Pull Request Completion Rule

Before opening a pull request, complete the manual static documentation-consistency review in this file and state the authoritative-document impact in the description. State which authoritative documents changed, or explain why none were affected. Use `.github/pull_request_template.md`.

Do not add automated enforcement for documentation completeness: no GitHub Action, documentation linter, semantic consistency script, link checker, pre-commit hook, commit hook, required status check, generator, or dependency. Clear repository policy and the pull-request template are the lightweight enforcement mechanism.
