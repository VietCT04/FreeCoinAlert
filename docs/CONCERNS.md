# Concerns

## Purpose

This document records unresolved current risks and decisions, not feature history or a backlog.

## Active Product Concerns

### Signal occurrence visibility and feed

**Current fact:** Global signal occurrences and subscription visibility state exist, but no feed API or browser feed exists.

**Risk/impact:** Users cannot consume the market facts that subscriptions select.

**Current mitigation:** Preset/version and occurrence snapshots preserve future-safe data.

**Follow-up:** Define and implement the owned feed contract and UI without duplicating global occurrences.

**Owning document:** [ALERTS.md](ALERTS.md).

## Active Security Concerns

### Process-local abuse limits

**Current fact:** Authentication, Telegram, alert, and signal limits are in-memory per API process.

**Risk/impact:** Multiple replicas or an untrusted proxy can bypass intended aggregate limits or identify IPs incorrectly.

**Current mitigation:** Current local deployment uses one API process and does not trust forwarded client identity.

**Follow-up:** Choose a trusted-proxy and shared rate-limit design before multi-replica/public deployment.

**Owning document:** [SECURITY.md](SECURITY.md).

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

## Active Operational Concerns

### No scheduler or production deployment automation

**Current fact:** Catalog synchronization, bootstrap, reconciliation, retention, and optional provider processes require explicit operator action or the stream's limited in-process cadence.

**Risk/impact:** Maintenance may be missed and production rollout/recovery is manual.

**Current mitigation:** Commands are bounded, singleton-protected where needed, and documented.

**Follow-up:** Approve a production operations design before relying on unattended service.

**Owning document:** [OPERATIONS.md](OPERATIONS.md).

## Active Verification Gaps

### No end-to-end runtime verification

**Current fact:** No provider, worker, migration, Compose, browser, or maintenance command has been run for the approved documentation work.

**Risk/impact:** Current-state documentation records implemented contracts, not evidence of exercised runtime behavior.

**Current mitigation:** Documentation labels these paths unverified and avoids delivery guarantees.

**Follow-up:** Maintain an explicit verification plan when the maintainer requests one.

**Owning document:** [OBSERVABILITY.md](OBSERVABILITY.md).

## Deferred Decisions

### Production observability design

**Current fact:** Structured logs and operational tables exist; metrics, dashboards, tracing, and alerts do not.

**Risk/impact:** Incident detection and diagnosis do not scale beyond manual inspection.

**Current mitigation:** Safe log categories and persisted state expose basic operator indicators.

**Follow-up:** Select and implement a production observability design with metrics and health dependencies.

**Owning document:** [OBSERVABILITY.md](OBSERVABILITY.md).
