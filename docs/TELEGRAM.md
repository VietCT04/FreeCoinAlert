# Telegram

## Purpose

This document defines Telegram account linking, bot-update handling, destination ownership, notification delivery, retries, disconnection, and user-facing behavior.

## Initial Scope

Telegram is the primary notification channel for the MVP.

The initial product should support a user's private chat with the FreeCoinAlert bot. Group and channel destinations require a later explicit decision.

## Connection Flow

Recommended flow:

1. An authenticated user selects **Connect Telegram**.
2. The API creates a securely random, short-lived, single-use token.
3. The web application opens a deep link equivalent to:

```text
https://t.me/<bot_username>?start=<token>
```

4. The user starts the bot.
5. Telegram sends the `/start <token>` update.
6. The backend validates and consumes the token.
7. The Telegram chat is linked to the authenticated user.
8. The bot sends a confirmation message.

The user must not be required to find or type a chat ID.

## Link Token Rules

A connection token must:

- Use cryptographically secure randomness.
- Expire within a short documented period.
- Be usable once.
- Be bound to the authenticated user who created it.
- Not expose the internal user ID.
- Be invalidated after successful use.
- Be stored as a hash where practical.
- Be rejected after expiration, use, or revocation.

Creating tokens should be rate-limited.

Issue #19 persists only the token lifecycle boundary: a user-bound SHA-256 binary hash,
explicit creation, expiry, consumption, and revocation timestamps, and one outstanding
unconsumed, unrevoked token per user. Issuing a replacement will revoke all outstanding
tokens, including expired rows, in Issue #20. No raw token generation or deep-link
construction is implemented here.

## Update Processing

Telegram updates may be received through webhook or long polling depending on environment.

Production should generally prefer a webhook with HTTPS and Telegram's supported secret-token mechanism.

Required behavior:

- Process updates idempotently using the Telegram update identifier.
- Reject malformed or unsupported commands safely.
- Avoid logging full sensitive payloads.
- Separate public webhook handling from internal business logic.
- Do not create duplicate connections from repeated updates.

Issue #19 stores only the `BIGINT` update identifier, a constrained processing outcome,
optional connection reference, operational timestamps, and optional confirmation-sent
timestamp. The update marker must be inserted in the same transaction as future linking
state changes so a rollback leaves the update retryable. Processed updates are eligible
for deletion after 30 days; the future processor may invoke bounded cleanup with an
explicit UTC cutoff. There is no webhook, polling, parsing, or Bot API integration yet.

## Stored Connection Data

Store the minimum needed information:

- User ID
- Telegram chat ID
- Connection status
- Telegram username only when useful for display or support
- Telegram user ID when required to validate private-chat ownership
- Connected and last-verified timestamps
- Last delivery failure category when operationally useful

Do not expose raw chat IDs unnecessarily.

## Ownership

- A user may view, test, update, or disconnect only destinations linked to their own account.
- A chat must not be silently reassigned between application users.
- Reconnecting an already linked chat requires an explicit safe rule.
- Administrative inspection must be authorized and audited when introduced.

The initial persistence rule permits one private-chat connection record per user.
Telegram user IDs and chat IDs are unique and are never silently transferred to a
different FreeCoinAlert user, even after disconnection. Account deletion cascades to the
connection and releases those identifiers; cross-account recovery is deferred.

## Test Notification

A test-notification action should:

- Require authentication.
- Operate only on the current user's destination.
- Be rate-limited.
- Use the normal durable notification path where practical.
- Report whether the message was queued rather than claiming delivery before Telegram confirms the send request.

## Alert Message Content

An alert message should clearly show:

- Symbol and market
- Signal or condition name
- Timeframe when relevant
- Trigger price
- Evaluation mode, especially candle close
- Trigger time
- A safe link back to the application when available

Example:

```text
BTCUSDT MACD Alert

MACD crossed above the signal line.
Timeframe: 15m
Evaluation: Candle close
Price: 118,420.50 USDT
Triggered: 2026-07-28 09:15 UTC
```

Do not claim that the alert predicts future price movement.

## Durable Delivery

Telegram messages must be created through the notification outbox.

The notification worker should:

1. Claim a pending job safely.
2. Send the message.
3. Record Telegram's response identifier where useful.
4. Mark the job sent.
5. Retry temporary failures with bounded backoff.
6. Mark permanent failures explicitly.

Do not send directly within the alert-evaluation transaction.

## Failure Categories

Distinguish at least:

- Temporary network or provider failure
- Telegram rate limit
- Bot blocked by user
- Chat not found or unavailable
- Invalid bot configuration
- Invalid message content
- Unknown provider failure

Respect Telegram retry guidance when present.

When the bot is blocked or a destination becomes permanently unavailable:

- Mark the connection degraded or disconnected according to the approved state model.
- Stop endless retries.
- Surface the problem in the web application.

## Duplicate Prevention

A notification job must have a stable idempotency relationship to its alert event and destination.

Repeated worker execution, API timeouts, or provider retries must not create duplicate messages when the outcome is already known.

When the provider outcome is uncertain, record the uncertainty rather than blindly retrying without a defined policy.

## Disconnect Flow

The user should be able to disconnect Telegram from the web application.

Disconnecting should:

- Require authentication.
- Disable future delivery to that destination.
- Preserve historical alert and delivery records according to retention policy.
- Invalidate outstanding linking tokens.
- Define whether active alerts are paused, remain active without a channel, or are disabled.

The exact product behavior requires a focused issue.

## Secrets

Never commit or log:

- Telegram bot token
- Telegram webhook secret
- Raw one-time linking tokens

Use environment variables or an approved secret manager.

## Testing Expectations

Use mocked Telegram clients and deterministic updates for:

- Successful linking
- Expired and reused tokens
- Duplicate updates
- Ownership enforcement
- Test-notification rate limiting
- Temporary delivery retry
- Bot-blocked permanent failure
- Disconnect behavior

Normal tests must not send real Telegram messages.

## Pending Decisions

- Webhook versus long polling for each environment.
- One destination versus multiple destinations per user.
- Private chats only versus group support.
- Connection and delivery status enums.
- Message formatting and localization.
- Behavior of active alerts after Telegram disconnects.
