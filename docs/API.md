# API

## Purpose

This document defines API-wide conventions and the planned resource areas. Exact endpoint contracts must be added by the GitHub Issue that implements them.

## Status

The API foundation currently implements only the unauthenticated process-health endpoint below. All feature resource groups remain planned.

Do not treat the examples below as final contracts. They define naming and behavior expectations for future implementation.

## Implemented Endpoints

### API Process Health

`GET /health`

Requires no authentication and returns HTTP `200` when the API process is running.

Response:

```json
{
  "status": "ok",
  "service": "freecoinalert-api"
}
```

This is liveness/process health only. It performs no database or external-network calls and does not represent readiness for PostgreSQL, market-data ingestion, alert evaluation, Telegram delivery, or future workers. Standard FastAPI OpenAPI endpoints remain available at `/docs`, `/redoc`, and `/openapi.json`.

## General Conventions

- Use JSON request and response bodies unless a documented endpoint requires another format.
- Use HTTPS outside local development.
- Authenticate server-side and derive the acting user from the authenticated principal.
- Never accept a client-provided `userId` as proof of ownership.
- Validate every request using shared schemas.
- Return stable machine-readable error codes with safe user-facing messages.
- Use UTC ISO 8601 timestamps in API contracts.
- Use explicit pagination for collection endpoints.
- Make retryable create operations idempotent where duplicate processing has meaningful effects.
- Do not expose provider secrets, raw stack traces, or another user's data.

## Planned Resource Groups

### Authentication and Current User

Expected responsibilities:

- Sign up, sign in, sign out, and current-user retrieval.
- Session or token validation.
- Account-level preferences such as display timezone.

Final endpoints depend on the approved authentication design.

### Telegram Connections

Expected responsibilities:

- Create a short-lived Telegram linking token.
- Read the current user's Telegram connection state.
- Send a test notification.
- Disconnect a destination.

Sensitive linking tokens must not be returned after use or stored in plaintext when avoidable.

### Supported Markets

Expected responsibilities:

- List supported exchanges, market types, symbols, timeframes, indicators, operators, and parameter constraints.
- Expose only combinations the backend can actually evaluate.

### Signal Templates

Expected responsibilities:

- List active platform-provided templates.
- Read a template version and its user-facing explanation.
- Subscribe to a specific version.

### User Alerts

Expected responsibilities:

- Create a template subscription or custom alert.
- List alerts owned by the current user.
- Read, update, pause, resume, and delete an owned alert.
- Validate rule definitions and usage limits server-side.

### Alert Events and Deliveries

Expected responsibilities:

- List triggered events for the current user's alerts.
- Show whether notification delivery is pending, sent, retrying, or failed.
- Never expose another user's destination details.

### Future Historical Analysis

Expected responsibilities:

- Submit an analysis job after validating strategy, date range, and data coverage.
- Read job state and results.
- Include assumptions, strategy version, sample size, fees, slippage, and date range.

Historical endpoints are out of scope for the alert-only MVP.

## Error Shape Direction

A future standard error response should contain fields equivalent to:

```json
{
  "code": "ALERT_RULE_INVALID",
  "message": "The alert rule contains an unsupported condition.",
  "details": [
    {
      "field": "trigger.conditions[0].operator",
      "reason": "UNSUPPORTED_VALUE"
    }
  ],
  "requestId": "..."
}
```

Do not include secrets, provider payloads, SQL details, or stack traces.

## Authorization Rules

- Users may access only their own alerts, Telegram connections, event history, and delivery records.
- Platform-template administration requires explicit admin authorization when introduced.
- Internal market-data and notification-worker actions must not be exposed as unrestricted public endpoints.
- Test-notification and alert-creation endpoints require rate limiting.

## Contract Change Rules

When an endpoint is added or changed:

1. Update shared DTOs and validation schemas.
2. Update backend behavior.
3. Update all frontend consumers.
4. Add or update authorization and validation tests where practical.
5. Update this document with the exact method, path, request, response, errors, and ownership rules.
6. Record incompatible changes explicitly rather than silently changing response shapes.

## Pending Decisions

- Authentication approach and session transport.
- API versioning strategy.
- Pagination format.
- Standard error-code registry.
- Whether public market metadata is served through the API or generated into the frontend build.
