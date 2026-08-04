# Browser E2E Coverage

## Purpose

This matrix owns the current browser-journey coverage for authentication, the dashboard shell, Telegram, one-time price alerts, and preset signals. It records the user-visible action or state, the specification that exercises it, and the setup boundary used by that specification. `Implemented / Unverified` means the journey is present in the repository but has not received a maintainer-requested browser pass.

The suite uses the real web application and API over the isolated Compose network. Authentication tests create accounts through the UI. Feature tests may create the owner through the normal authenticated API request context, then use a real browser session. Provider events and Telegram outcomes come from the internal provider simulator. The guarded E2E control service is limited to Telegram-link expiry and high-volume pagination fixtures; it does not create users or replace ordinary owner mutations.

## Current Journey Matrix

| Route | User action or visible state | Specification | Test title | Setup source | Status |
| --- | --- | --- | --- | --- | --- |
| `/dashboard`, `/price-alerts`, `/preset-signals`, `/historical-analysis`, `/telegram` | Anonymous navigation redirects to sign-in | `apps/e2e/specs/auth.spec.ts` | redirects anonymous users from every protected dashboard route | UI only | Implemented / Unverified |
| `/sign-up` | Required fields, short password, mismatch, successful registration | `apps/e2e/specs/auth.spec.ts` | enforces sign-up validation and creates an account through the form | UI only | Implemented / Unverified |
| `/sign-up` | Normalized duplicate email uses a safe message | `apps/e2e/specs/auth.spec.ts` | rejects a duplicate normalized email without exposing account details | UI only | Implemented / Unverified |
| `/sign-in`, `/dashboard` | Bad credentials, correct credentials, reload restoration, sign-out | `apps/e2e/specs/auth.spec.ts` | supports bad credentials, correct credentials, sign-out, and reload restoration | UI only | Implemented / Unverified |
| `/dashboard` | A second request context logs out the active session and the next browser action redirects | `apps/e2e/specs/auth.spec.ts` | redirects the next browser action after a second request context logs out | UI plus second real API request context | Implemented / Unverified |
| `/sign-in` | Sign-out leaves no browser storage authentication or CSRF state | `apps/e2e/specs/auth.spec.ts` | does not leave authentication or CSRF state in browser storage after sign-out | UI only | Implemented / Unverified |
| `/dashboard`, `/price-alerts`, `/preset-signals`, `/historical-analysis`, `/telegram` | Desktop landmarks, route links, active route, breadcrumbs, skip link | `apps/e2e/specs/dashboard.spec.ts` | renders landmarks, navigation, skip link, active route, and breadcrumbs | UI plus authenticated API session | Implemented / Unverified |
| `/dashboard`, mobile | Drawer focus containment, Escape, destination links, current route | `apps/e2e/specs/dashboard.mobile.spec.ts` | opens a focus-contained drawer, navigates every destination, and returns focus on Escape | UI plus authenticated API session | Implemented / Unverified |
| `/price-alerts`, mobile | Outside interaction closes drawer and preserves route announcement | `apps/e2e/specs/dashboard.mobile.spec.ts` | closes the drawer from an outside interaction and preserves the current destination announcement | UI plus authenticated API session | Implemented / Unverified |
| `/dashboard` | Account menu, Escape/focus return, light/dark/system theme reload | `apps/e2e/specs/dashboard.spec.ts` | supports account-menu focus behavior and persistent light, dark, and system themes | UI plus authenticated API session | Implemented / Unverified |
| `/dashboard` | Primary links and refresh action use real routes | `apps/e2e/specs/dashboard.spec.ts` | keeps the primary dashboard actions connected to their real routes | UI plus authenticated API session | Implemented / Unverified |
| `/dashboard` | Empty and populated owner activity | `apps/e2e/specs/dashboard.spec.ts` | shows empty and populated owner activity states | UI plus normal API owner record and provider simulator | Implemented / Unverified |
| `/telegram` | Disconnected readiness and blocked test notification | `apps/e2e/specs/telegram.spec.ts` | shows the disconnected readiness state and prevents test delivery | UI plus authenticated API session | Implemented / Unverified |
| `/telegram` | Linking state and expired generated link | `apps/e2e/specs/telegram.spec.ts` | exposes linking state and handles an expired generated link | Normal API link plus guarded expiry control | Implemented / Unverified |
| `/telegram` | Connected state, refresh, confirmed disconnect | `apps/e2e/specs/telegram.spec.ts` | connects through the real poller, refreshes status, and confirms disconnect | UI plus provider simulator linking/poller | Implemented / Unverified |
| `/telegram` | Provider-accepted test notification | `apps/e2e/specs/telegram.spec.ts` | renders a successful provider-accepted test notification | UI plus provider simulator | Implemented / Unverified |
| `/telegram` | Temporary failure and rate-limit retry state | `apps/e2e/specs/telegram.spec.ts` | exposes temporary and rate-limited provider outcomes as pending retry states | UI plus provider simulator | Implemented / Unverified |
| `/telegram` | Permanent failure state | `apps/e2e/specs/telegram.spec.ts` | keeps permanent and uncertain provider outcomes distinct | UI plus provider simulator | Implemented / Unverified |
| `/telegram` | Uncertain provider outcome does not claim delivery | `apps/e2e/specs/telegram.spec.ts` | surfaces an uncertain provider result without claiming delivery | UI plus provider simulator | Implemented / Unverified |
| `/price-alerts` | Telegram readiness restriction before creation | `apps/e2e/specs/price-alerts.spec.ts` | requires Telegram readiness before an alert can be activated | UI plus authenticated API session | Implemented / Unverified |
| `/price-alerts` | Dialog focus, market/direction, minimum/precision validation, preview, one browser create | `apps/e2e/specs/price-alerts.spec.ts` | supports dialog focus, condition, target validation, preview, and exactly one browser create | UI plus connected provider simulator | Implemented / Unverified |
| `/price-alerts` | Server idempotency, waiting, monitoring, crossing, trigger, delivery queued | `apps/e2e/specs/price-alerts.spec.ts` | preserves server idempotency and renders live waiting, monitoring, crossing, and delivery states | Normal API owner record plus provider simulator | Implemented / Unverified |
| `/price-alerts` | Market-data disconnect warning and terminal deletion behavior | `apps/e2e/specs/price-alerts.spec.ts` | handles market-data warnings and terminal deletion rules | Normal API owner record plus provider simulator | Implemented / Unverified |
| `/price-alerts` | Active-limit safe UI error | `apps/e2e/specs/price-alerts.spec.ts` | renders the active-limit error without exposing server details | Guarded high-volume active fixture | Implemented / Unverified |
| `/price-alerts` | Rate-limit safe UI error | `apps/e2e/specs/price-alerts.spec.ts` | renders the rate-limit error without exposing server details | Ten normal API owner requests plus UI | Implemented / Unverified |
| `/price-alerts` | Owner-scoped disabled pagination, filter, cancel/confirm deletion | `apps/e2e/specs/price-alerts.spec.ts` | uses owner-scoped pagination, filter tabs, and confirmed deletion | Guarded high-volume fixture plus UI | Implemented / Unverified |
| `/preset-signals` | Market/timeframe/subscription filters, details, subscribe/disable/re-enable | `apps/e2e/specs/preset-signals.spec.ts` | filters the catalog, exposes fixed technical details, and manages a subscription lifecycle | UI plus authenticated API session | Implemented / Unverified |
| `/preset-signals` | Telegram readiness, confirmed preference enable/disable, history tab | `apps/e2e/specs/preset-signals.spec.ts` | confirms Telegram delivery readiness and keeps website history separate | Connected provider simulator plus UI | Implemented / Unverified |
| `/preset-signals` | Owner-visible history, current/invalidated rows, filters, pagination, View history focus | `apps/e2e/specs/preset-signals.spec.ts` | paginates owner-visible history, filters it, and handles sound activation and mute | Guarded high-volume signal-feed fixture plus UI | Implemented / Unverified |
| `/preset-signals` | Sound activation and mute | `apps/e2e/specs/preset-signals.spec.ts` | paginates owner-visible history, filters it, and handles sound activation and mute | UI gesture plus browser audio boundary | Implemented / Unverified |
| `/preset-signals`, Telegram | Deterministic live signal, one simulated Telegram delivery, and no duplicate visible entry | `apps/e2e/specs/preset-signals.spec.ts` | receives a deterministic live event and one Telegram delivery without duplicate entries | Normal API subscription, UI preference, provider simulator closed candles/messages | Implemented / Unverified |

## Excluded From #114

| Route or surface | Excluded combination | Reason | Status |
| --- | --- | --- | --- |
| `/historical-analysis` | Historical-analysis browser journeys | Explicitly out of scope for this issue; its current flow remains covered by the separate approved historical-analysis work. | Not applicable |
| All current routes | Complete cross-browser Firefox/WebKit coverage | The approved solution limits this issue to the pinned Chromium desktop/mobile projects. | Not applicable |
| All current routes | Full mobile/accessibility expansion beyond the dashboard shell | A mobile dashboard journey and existing accessibility result collection are included; a complete mobile/accessibility program is separate work. | Not applicable |
| All current routes | Visual snapshot/regression coverage | Explicitly out of scope. | Not applicable |
| All current routes | Production Binance or Telegram providers | The suite must use the isolated provider simulator. | Not applicable |
| All current routes | CI workflow or automated verification enforcement | The issue adds repository coverage and documentation only; runtime verification remains maintainer-requested. | Not applicable |
