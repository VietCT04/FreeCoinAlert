# User Stories

## Purpose

User stories describe product behavior from a user's perspective. They are the product source for creating focused implementation GitHub Issues.

A user story may cover a complete user outcome. Implementation issues should divide that outcome into small, independently verifiable slices.

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

As a [user type], I want [goal], so that [benefit].

## Context

Explain why this behavior matters and how it fits the product.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Authorization is enforced server-side where relevant
- [ ] External-event processing is idempotent where relevant
- [ ] Loading, empty, success, and error states are handled
- [ ] Relevant documentation is updated

## Risks

List product, security, reliability, market-data, delivery, or usability risks.

## Follow-up Issues

- GitHub Issue: `#123`
```

## Appropriate User Stories

Use stories for product-facing behavior such as:

- Create an account and sign in
- Connect or disconnect Telegram
- Browse available signal templates
- Subscribe to a signal
- Create a custom price or indicator alert
- Pause, resume, edit, or delete an alert
- Receive and view alert history
- Review notification delivery failure
- Request historical strategy analysis
- Manage supported templates as an administrator

## Story Workflow

1. Draft the user story with clear acceptance criteria.
2. Review product boundaries and relevant concerns.
3. Obtain user approval.
4. Create one or more focused GitHub Issues.
5. Add the issue links to the story.
6. Implement issues through pull requests.
7. Update the story when approved behavior changes.

## Issue-Splitting Guidance

Split work when a story includes independent areas such as:

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

Do not use a user story to silently approve unresolved security, data-quality, or financial-performance assumptions.