# Concerns

## Purpose

This document records unresolved current risks and decisions, not feature history or a backlog.

## Active Product Concerns

### Subscription reactivation can exceed the active limit

**Current fact:** New signal subscription rows are checked against the 20-enabled-subscription limit, but reactivation of an existing disabled row bypasses that count check.

**Risk/impact:** A user with 20 enabled subscriptions and another disabled subscription can reactivate it and exceed the intended active limit.

**Current mitigation:** Subscription creation is serialized per user, and duplicate active combinations are replayed rather than duplicated.

**Follow-up:** Add an active-count check to the reactivation branch in a separately approved implementation change.

**Owning document:** [ALERTS.md](ALERTS.md).

## Active Security Concerns

### Process-local abuse limits

**Current fact:** Authentication, Telegram, alert, subscription, signal-feed request, and SSE connection limits are in-memory per API process.

**Risk/impact:** Multiple replicas or an untrusted proxy can bypass intended aggregate limits or identify IPs incorrectly.

**Current mitigation:** Current local deployment uses one API process and does not trust forwarded client identity.

**Follow-up:** Choose a trusted-proxy and shared rate-limit design before multi-replica/public deployment.

**Owning document:** [SECURITY.md](SECURITY.md).

### Signal-feed proxy and replica deployment

**Current fact:** The API listener and SSE connection manager are process-local; every API replica receives PostgreSQL notifications independently, and the stream route requires proxy buffering and timeout settings.

**Risk/impact:** A multi-replica deployment has no aggregate connection count or shared rate-limit state, and an incorrectly buffering or short-lived proxy can delay heartbeats and live events.

**Current mitigation:** Durable stream cursors, bounded replay, reset recovery, no-transform cache headers, and documented proxy requirements prevent silent loss when a client reconnects.

**Follow-up:** Approve a production proxy, shared-limit, and cross-process observability design before public horizontal deployment.

**Owning document:** [OPERATIONS.md](OPERATIONS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Active Reliability and Data-Quality Concerns

### Provider paths are unverified

**Current fact:** Binance and Telegram runtime paths are implemented but have not received an explicit verification pass.

**Risk/impact:** Provider protocol, limits, reconnect, repair, and delivery behavior can differ from static expectations.

**Current mitigation:** Input validation, bounded retries, durable state, idempotency, and safe failure categories are implemented.

**Follow-up:** Run a maintainer-approved verification pass with controlled provider fixtures or environments.

**Owning document:** [MARKET_DATA.md](MARKET_DATA.md) and [TELEGRAM.md](TELEGRAM.md).

### Candle corrections require explicit rebuilding

**Current fact:** A candle revision makes affected signal evaluation stale; immutable signal events are not changed.

**Risk/impact:** Corrected history may remain without replacement/invalidation until a rebuild is performed.

**Current mitigation:** Correction state and invalidation-model boundaries exist.

**Follow-up:** Define and operate a bounded, verified correction rebuild runbook.

**Owning document:** [ALERTS.md](ALERTS.md).

### Catalog freshness split between API and stream

**Current fact:** API alert and subscription readiness uses `MARKET_CATALOG_MAX_AGE_SECONDS`, while the market stream uses a hardcoded 24-hour maximum instead of that setting.

**Risk/impact:** A setting change can cause the API and stream to disagree about market readiness.

**Current mitigation:** Both values default to 24 hours.

**Follow-up:** Align stream readiness with the configured setting in a separately approved code change.

**Owning document:** [MARKET_DATA.md](MARKET_DATA.md).

## Active Operational Concerns

### No scheduler or production deployment automation

**Current fact:** Outside the local Compose dependency graph, catalog synchronization, bootstrap, reconciliation, retention, and optional provider processes require explicit operator action or the stream's limited in-process cadence.

**Risk/impact:** Maintenance may be missed and production rollout/recovery is manual.

**Current mitigation:** Commands are bounded, singleton-protected where needed, and documented.

**Follow-up:** Approve a production operations design before relying on unattended service.

**Owning document:** [OPERATIONS.md](OPERATIONS.md).

## Active Verification Gaps

### No end-to-end runtime verification

**Current fact:** No provider, worker, migration, Compose initialization, browser, signal-stream, audio, or maintenance command has been run for the approved implementation work.

**Risk/impact:** Current-state documentation records implemented contracts, not evidence of exercised runtime behavior.

**Current mitigation:** Documentation labels these paths unverified and avoids delivery guarantees; Compose dependency conditions make initialization ordering explicit; browser signal and historical-analysis surfaces keep client presentation separate from provider work, live occurrences, and optional sound.

**Follow-up:** Maintain an explicit verification plan when the maintainer requests one.

**Owning document:** [OBSERVABILITY.md](OBSERVABILITY.md).

## Deferred Decisions

### Production observability design

**Current fact:** Structured logs and operational tables exist; metrics, dashboards, tracing, and alerts do not.

**Risk/impact:** Incident detection and diagnosis do not scale beyond manual inspection.

**Current mitigation:** Safe log categories and persisted state expose basic operator indicators.

**Follow-up:** Select and implement a production observability design with metrics and health dependencies.

**Owning document:** [OBSERVABILITY.md](OBSERVABILITY.md).
