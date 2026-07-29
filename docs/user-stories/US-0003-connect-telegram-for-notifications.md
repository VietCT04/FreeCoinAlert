# US-0003: Connect Telegram for Notifications

## User Story

As a signed-in user, I want to connect my Telegram account, so that FreeCoinAlert can send cryptocurrency alerts directly to me.

## Context

US-0002 establishes user accounts and authenticated ownership. Before users create alerts, the platform needs a secure way to connect each user to a Telegram destination.

Users should not manually enter Telegram chat IDs. The connection should use a short-lived, one-time linking process initiated from the FreeCoinAlert website.

## Acceptance Criteria

- [ ] A signed-in user can request a Telegram connection link.
- [ ] The connection link expires after a short period.
- [ ] The link can be used only once.
- [ ] Opening the link starts the FreeCoinAlert Telegram bot.
- [ ] The bot confirms when the Telegram account is connected successfully.
- [ ] The website shows whether Telegram is connected.
- [ ] A connected user can send a test notification.
- [ ] A user can disconnect their Telegram account.
- [ ] One user cannot connect, view, test, or disconnect another user’s Telegram destination.
- [ ] Telegram chat identifiers and linking secrets are not exposed unnecessarily.
- [ ] Relevant product, API, database, security, Telegram, and continuity documentation is updated.

## Out of Scope

- Creating or managing cryptocurrency alerts
- Telegram groups or channels
- Multiple Telegram destinations per user
- Email, SMS, Discord, or other notification providers
- Telegram webhook production deployment
- Message templates for triggered alerts
- Telegram bot administration UI

## Risks

- Linking tokens must be securely random, short-lived, single-use, and bound to the authenticated user.
- Telegram updates may be delivered more than once and must be processed idempotently.
- Disconnecting Telegram must prevent future notifications from being sent to the old destination.
- Telegram bot tokens and chat identifiers must not appear in logs or frontend responses unnecessarily.

## Follow-up Issues

- #19 - Add Telegram connection and linking-token persistence
- #20 - Implement authenticated Telegram connection API
- #21 - Implement Telegram bot update processing and account linking
- #22 - Add Telegram test-notification outbox and delivery worker
- #23 - Add frontend Telegram connection and test-notification flow

## Implementation Order

1. Complete US-0002 through Issues #11, #13, #14, and #15.
2. Implement Issue #19.
3. Implement Issue #20.
4. Implement Issue #21.
5. Implement Issue #22.
6. Implement Issue #23.

Each implementation issue requires an explicitly approved solution comment before implementation begins.
