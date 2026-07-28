# User Stories

## Purpose

User stories describe a valuable outcome from a stakeholder's perspective. A stakeholder may be an end user, project maintainer, developer, administrator, or another role affected by the system.

User stories are the product source for creating focused implementation GitHub Issues. A story may cover a complete stakeholder outcome, while implementation issues divide that outcome into small, independently verifiable slices.

Stories should remain short and avoid unnecessary technical implementation detail. Technical decisions belong in issue proposals after the user story is approved.

## Folder and Naming

Store stories in:

```text
docs/user-stories/
```

Use filenames:

```text
US-0001-short-title.md
US-0002-short-title.md
```

Numbers are sequential and never reused.

## Template

```md
# US-0001: Short Title

## User Story

As a [stakeholder type], I want [goal], so that [benefit].

## Context

Explain why this behavior matters and how it fits the product.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Authorization is enforced server-side where relevant
- [ ] External-event processing is idempotent where relevant
- [ ] Loading, empty, success, and error states are handled where relevant
- [ ] Relevant documentation is updated

## Out of Scope

List nearby work that is not part of this story.

## Risks

List product, security, reliability, market-data, delivery, development, or usability risks.

## Follow-up Issues

- GitHub Issue: `#123`
```

## Appropriate User Stories

Stories may describe outcomes for different stakeholders.

### Maintainers and developers

- Establish a consistent and runnable project foundation
- Provide a repeatable local-development workflow
- Add reliable deployment or operational capabilities

### End users

- Create an account and sign in
- Connect or disconnect Telegram
- Browse available signal templates
- Subscribe to a signal
- Create a custom price or indicator alert
- Pause, resume, edit, or delete an alert
- Receive and view alert history
- Request historical strategy analysis

### Administrators and support roles

- Manage supported symbols or signal templates
- Review notification-delivery failures
- Investigate market-data gaps

## Story Workflow

1. Propose a short stakeholder-focused user story with clear acceptance criteria.
2. Review product boundaries and relevant concerns.
3. Obtain explicit user approval.
4. Create a documentation-only pull request that adds the approved story and updates relevant docs.
5. Create focused GitHub Issues linked to the approved story.
6. Add the issue links to the user-story document in the same pull request.
7. When requested, propose a technical solution for one issue in the conversation.
8. Revise the solution until the user explicitly approves it.
9. Post the approved solution as a comment on that GitHub Issue so implementation agents can follow it.
10. Implement approved issues through separate pull requests.
11. Update the story only when approved behavior changes.

Do not add an unapproved technical solution to an issue comment.

## Issue-Splitting Guidance

Split work when a story includes independent areas such as:

- Repository or developer tooling
- Database schema
- API contract
- Frontend flow
- Telegram integration
- Market-data processing
- Alert evaluation
- Security or rate limiting
- Observability

Example for **Connect Telegram**:

1. Persist connection and linking-token models.
2. Create authenticated link-token API.
3. Process Telegram `/start` updates.
4. Add frontend connection flow.
5. Add disconnect and test-notification behavior.

Each issue should have one primary outcome and independently verifiable acceptance criteria.

## Required Cross-Checks

Before approving a story, check:

- [`../PRODUCT.md`](../PRODUCT.md)
- [`../SECURITY.md`](../SECURITY.md)
- The relevant domain document
- [`../CONCERNS.md`](../CONCERNS.md)

Do not use a user story to silently approve unresolved security, data-quality, infrastructure, or financial-performance assumptions.
