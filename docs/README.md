# Documentation Guide

## Current-State Rule

Current behavior is derived from merged code and the authoritative domain documents below. Read the relevant documents before changing a domain, and update their current-state contract in the same pull request. A document may provide brief context and a relative link to another owner; it must not reproduce that owner's detailed contract.

## Status Vocabulary

Use availability and verification as independent dimensions.

| Dimension | Term | Meaning |
| --- | --- | --- |
| Availability | Implemented | Present in merged `main`. |
| Availability | Planned | Approved or discussed, but absent from merged `main`. |
| Availability | Not supported | Deliberately unavailable now. |
| Availability | Unresolved | A decision or risk remains open. |
| Verification | Verified | An explicit maintainer-requested verification pass exercised the behavior. |
| Verification | Unverified | Implementation exists, but no such pass exercised it. |
| Verification | Not applicable | No runtime behavior exists to exercise. |

Implemented does not imply Verified. Planned is absent, not Unverified. Do not use vague status words such as “done,” “ready,” “complete,” or “working” when availability or verification is the intended meaning.

## Reading Paths

- New product contributor: [PRODUCT.md](PRODUCT.md) → [ARCHITECTURE.md](ARCHITECTURE.md) → relevant domain → [CONCERNS.md](CONCERNS.md) → [CONTINUITY.md](CONTINUITY.md) → [AGENTS.md](../AGENTS.md).
- API/backend change: [ARCHITECTURE.md](ARCHITECTURE.md) → [API.md](API.md) → [DATABASE.md](DATABASE.md)/[SECURITY.md](SECURITY.md) → relevant runtime domain → [CONCERNS.md](CONCERNS.md) → [AGENTS.md](../AGENTS.md).
- Frontend change: [PRODUCT.md](PRODUCT.md) → [API.md](API.md) → [SECURITY.md](SECURITY.md) → relevant feature domain → [AGENTS.md](../AGENTS.md).
- Operations or incident work: [OPERATIONS.md](OPERATIONS.md) → [OBSERVABILITY.md](OBSERVABILITY.md) → relevant runtime domain → [CONCERNS.md](CONCERNS.md) → [CONTINUITY.md](CONTINUITY.md).
- E2E environment or verification work: [TESTING.md](TESTING.md) → [E2E_COVERAGE.md](E2E_COVERAGE.md) → [OPERATIONS.md](OPERATIONS.md) → affected runtime domain → [SECURITY.md](SECURITY.md) → [CONCERNS.md](CONCERNS.md).
- Planning: [PRODUCT.md](PRODUCT.md) → [user story](user-stories/README.md) → GitHub issue and approved comment.

## Authoritative Ownership

| Document | Sole detailed owner |
| --- | --- |
| [`PRODUCT.md`](PRODUCT.md) | Current user-visible capabilities, journeys, limits, and non-goals. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Current repository/runtime topology, component ownership, process boundaries, and data flows. |
| [`API.md`](API.md) | Current HTTP methods, paths, authentication, requests, responses, errors, caching, pagination, rate limits, and ownership contracts. |
| [`DATABASE.md`](DATABASE.md) | Current tables, columns, types, relationships, constraints, indexes, lifecycle storage, transactions, retention, and migration inventory. |
| [`SECURITY.md`](SECURITY.md) | Current trust boundaries, authentication, CSRF, authorization, secrets, abuse controls, redaction, and exposure rules. |
| [`MARKET_DATA.md`](MARKET_DATA.md) | Current provider catalog, streams, candles, aggregation, repair, correction, freshness, and retention behavior. |
| [`ALERTS.md`](ALERTS.md) | Current price-alert and preset-signal lifecycle, crossing, trigger, event, invalidation, and deduplication behavior. |
| [`STRATEGIES.md`](STRATEGIES.md) | Current preset definitions, calculation versions, formulas, inputs, warm-up, outcomes, and strategy compatibility. |
| [`TELEGRAM.md`](TELEGRAM.md) | Current Telegram linking, update processing, outbox delivery, retry, and provider-status behavior. |
| [`OPERATIONS.md`](OPERATIONS.md) | Current commands, processes, profiles, configuration, maintenance, recovery, and production gaps. |
| [`OBSERVABILITY.md`](OBSERVABILITY.md) | Current health, persistent states, structured logs, measurements, freshness, redaction, and incident indicators. |
| [`BACKTESTING.md`](BACKTESTING.md) | Current availability and future historical-analysis semantic requirements. |
| [`TESTING.md`](TESTING.md) | Current verification boundary and isolated E2E environment contract. |
| [`CONCERNS.md`](CONCERNS.md) | Genuinely unresolved current risks, assumptions, limitations, and decisions. |
| [`CONTINUITY.md`](CONTINUITY.md) | Current handoff only: snapshot, active work, blockers, verification state, and next actions. |
| [`user-stories/*.md`](user-stories/README.md) | Approved requirements and planning history, not the source of current implementation behavior. |

## History and Planning Boundary

GitHub issues and pull requests preserve implementation history. User stories preserve approved requirements and can include criteria beyond the current merged implementation. Check the authoritative domain documents for current availability; do not rewrite historical stories to add implementation status.

## Update Rule

Replace stale, incomplete, superseded, or contradictory statements instead of appending issue-by-issue diaries. Review related documentation, README entry points, environment examples, and [CONTINUITY.md](CONTINUITY.md) for changes that affect behavior, contracts, configuration, operations, or status.
