# US-0006: Maintain Current-State Product and Technical Documentation

## User Story

As a project maintainer, I want all documentation to describe the complete current behavior of FreeCoinAlert by domain, so that developers can understand and modify the system without reconstructing it from old issues, pull requests, or implementation history.

## Context

The current documentation often records changes as an implementation history:

- Issue or pull request summaries are appended to domain and continuity documents.
- Old pending statements remain after the related behavior is implemented.
- New sections are added without replacing superseded rules.
- Readers must combine several historical updates to determine how the system currently works.

The repository documentation must instead be organized around the current product and technical domains. Issues and pull requests may explain why a change was introduced, but they must not be required to understand the current system.

Authoritative domain ownership should remain clear:

- `PRODUCT.md` owns current user-facing behavior, scope, and limitations.
- `ARCHITECTURE.md` owns current components, responsibilities, processes, and data flows.
- `API.md` owns current endpoint and error contracts.
- `DATABASE.md` owns the current schema, relationships, constraints, indexes, lifecycles, and retention.
- `MARKET_DATA.md` owns the complete current market-data flow and data-quality rules.
- `ALERTS.md` owns current alert and signal lifecycle and evaluation behavior.
- `STRATEGIES.md` owns current preset and indicator semantics.
- `TELEGRAM.md` owns current Telegram linking and delivery behavior.
- `SECURITY.md` owns current authentication, authorization, secrets, logging, and trust boundaries.
- `OPERATIONS.md` owns current configuration, processes, commands, recovery, and maintenance tasks.
- `OBSERVABILITY.md` owns current health, logs, metrics, freshness, and incident signals.

## Acceptance Criteria

- [ ] Every domain document describes the complete current implemented behavior for that domain.
- [ ] Main domain documents are organized by responsibility and system behavior rather than issue or pull-request history.
- [ ] Issue and pull-request references are removed from current-state explanations unless genuinely needed for a decision or handoff.
- [ ] Historical information remains in GitHub, ADRs, changelogs, or concise handoff records rather than replacing domain documentation.
- [ ] Documentation clearly separates implemented behavior, planned behavior, and unresolved concerns.
- [ ] Implemented behavior is not described as pending, and unimplemented behavior is not described as available.
- [ ] Documentation updates replace stale rules rather than only appending new issue-specific paragraphs.
- [ ] Contradictory, duplicated, superseded, and outdated statements are removed.
- [ ] API documentation contains the complete current request, response, authentication, authorization, pagination, rate-limit, lifecycle, and error contracts.
- [ ] Database documentation contains the complete current tables, columns, relationships, constraints, indexes, lifecycle rules, transaction boundaries, and retention behavior.
- [ ] Architecture documentation contains the complete current processes, components, ownership boundaries, dependencies, and data flows.
- [ ] Product documentation contains the complete current user flows, supported capabilities, and limitations.
- [ ] Security documentation contains the complete current authentication, CSRF, authorization, secrets, provider, logging, and data-exposure boundaries.
- [ ] Operational documentation contains the complete current commands, environment settings, process profiles, startup requirements, and maintenance tasks.
- [ ] Each important concept has one authoritative documentation location.
- [ ] Other documents link to the authoritative location rather than copying detailed rules that may diverge.
- [ ] Relevant root, application, and service READMEs remain concise entry points and link to authoritative domain documents.
- [ ] `CONTINUITY.md` becomes a concise current handoff containing current state, active work, blockers, unresolved concerns, and next steps rather than a completed-issue diary.
- [ ] `AGENTS.md` requires agents to read authoritative current-state documentation before changing code.
- [ ] `AGENTS.md` requires every behavior-changing pull request to update all affected authoritative documentation in the same change.
- [ ] `AGENTS.md` requires replacement of stale statements and a final cross-document consistency review.
- [ ] A repository-wide documentation audit corrects existing stale, historical, duplicated, and contradictory content.

## Documentation Rules

### Current-State Rule

Domain documentation must answer:

```text
How does the system work now?
```

It must not require the reader to reconstruct behavior from issue chronology.

### Same-Change Rule

When code changes product behavior, APIs, schema, authentication, security, market data, alerts, strategies, notifications, frontend behavior, processes, configuration, operations, observability, failure handling, or recovery, the same pull request must update every affected authoritative document.

### Replacement Rule

When behavior changes:

- Replace the old rule with the new rule.
- Remove obsolete examples and pending statements.
- Update affected tables, diagrams, lifecycle descriptions, contracts, commands, and configuration.
- Do not append an issue-specific completion note as a substitute for updating the existing explanation.

### Ownership Rule

Each important concept must have one authoritative document. Other documents include only the context needed for their domain and link to the authoritative explanation.

For example:

```text
DATABASE.md owns exact table definitions and constraints.
ALERTS.md owns alert-domain behavior.
ARCHITECTURE.md explains how alert components interact without duplicating every column.
```

### History Separation Rule

Historical information belongs in GitHub issues, pull requests, ADRs, changelogs, or concise handoff records. It must not replace current-state system documentation.

## Out of Scope

- Rewriting closed GitHub issues or pull requests
- Building or publishing a documentation website
- Creating marketing content or end-user tutorials
- Adding a large documentation framework
- Requiring an ADR for every normal implementation change
- Keeping detailed issue-by-issue history inside domain documents
- Implementing unrelated product behavior

## Risks

- A repository-wide cleanup could accidentally remove important current behavior unless code and documentation are reviewed together.
- Ownership boundaries must be explicit to prevent the same rule from diverging across several documents.
- Future contributors may return to appending issue summaries unless `AGENTS.md` is unambiguous.
- Documentation may claim runtime behavior is verified when implementation exists but has not been exercised.
- `CONTINUITY.md` may become stale again if it duplicates authoritative domain details.

## Follow-up Issues

- #61 — Rewrite core product and system contracts as current state
- #62 — Rewrite runtime and domain behavior as current state
- #63 — Establish documentation ownership, navigation, and concise handoff
- #64 — Enforce current-state documentation in contributor workflow

Implementation order:

```text
#61 → #62 → #63 → #64
```

Each implementation issue requires an explicitly approved technical solution comment before work begins.
