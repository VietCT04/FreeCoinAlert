# US-0010: Redesign the Web App with shadcn Dashboard

## Status

Approved

## User Story

As a FreeCoinAlert user, I want a clear, modern, responsive dashboard that organizes alerts, preset signals, historical analysis, and Telegram into understandable workflows, so that I can use the product without scanning one long, visually inconsistent page.

## Approved Design Direction

Use the shadcn/ui `dashboard-01` block as the structural and visual starting point.

Approved stack:

- Existing Next.js App Router application
- Existing React and TypeScript application
- Existing Tailwind CSS 4 configuration
- shadcn/ui repository-owned components
- `New York` component style
- Neutral or zinc base palette
- Radix-based accessible primitives used by shadcn/ui
- Lucide React icons
- shadcn chart composition with Recharts for historical-analysis equity data
- Sonner for transient non-sensitive feedback where appropriate
- Light and dark themes

The template is a starting structure, not a replacement application. Do not import its fake data, unrelated analytics, duplicate authentication, Prisma, RBAC, billing, team management, or demo pages.

## Context

FreeCoinAlert now supports:

- User registration, authentication, session restoration, and logout
- Controlled Binance Spot markets
- One-time price alerts
- Fixed preset subscriptions
- Historical and live preset-signal feed
- Browser signal sound
- Private Telegram linking and test messages
- Telegram delivery for price alerts and opted-in preset signals
- Historical fixed-preset analysis with persisted reports, trades, and equity data

These capabilities are functionally separated in backend contracts, but the browser presentation has grown inside a dense root-page experience. The redesign must improve information architecture and visual quality without changing the existing domain, security, provider, ownership, or calculation behavior.

## Primary User Experience

After authentication, the user enters a responsive dashboard shell with these primary destinations:

1. Overview
2. Price Alerts
3. Preset Signals
4. Historical Analysis
5. Telegram

Desktop uses a collapsible sidebar. Mobile uses an accessible drawer or equivalent compact navigation. The header provides the current page, navigation context, theme control, and user/session actions.

## Overview Requirements

The overview helps the user answer:

- Is market monitoring available?
- How many active alerts and preset subscriptions do I have?
- Is Telegram connected and available?
- What recent owner-visible activity occurred?

Use only existing safe APIs and supported state. Do not invent delivery history, provider receipt claims, revenue analytics, portfolio values, recommendations, or fake template data.

Provide clear primary actions for creating a price alert and browsing fixed presets.

## Price Alert Requirements

The price-alert page must:

- Show active and terminal alerts in a clear card or table layout.
- Make market, crossing direction, target price, state, and notification behavior understandable.
- Put creation in an accessible dialog or responsive drawer.
- Preserve existing market validation, exact decimal handling, lifecycle, ownership, CSRF, rate limits, confirmation, safe errors, and server-confirmed state.
- Provide clear loading, empty, pending, unavailable, stale-session, and failure states.

No new alert type or backend behavior is introduced by this story.

## Preset Signal Requirements

The preset-signal page must:

- Present the controlled preset catalogue in understandable cards.
- Support clear filtering by market, timeframe, and subscription state using existing data.
- Keep fixed formula, version, direction, period, threshold, calculation version, and description available without overwhelming the default view.
- Preserve subscribe, disable, Telegram-delivery preference, readiness, confirmation, and safe-error behavior.
- Separate catalogue/subscription controls from signal history through clear tabs or sections.
- Preserve historical pagination, SSE live delivery, replay/reset recovery, invalidation, cursor ordering, browser sound, session revalidation, ownership, and accessibility semantics.

No custom formula, editable parameter, additional preset, or delivery-history feature is introduced.

## Telegram Requirements

The Telegram page must:

- Show connected, linking, degraded, disconnected, and unavailable states clearly.
- Guide the user through private-chat linking without exposing sensitive provider identifiers.
- Preserve test-message, reconnect, disconnect, readiness refresh, CSRF, ownership, safe-token, and provider-error behavior.
- Summarize which existing alert and preset-subscription preferences use Telegram where this can be derived safely from existing responses.

Telegram state remains server-owned. It must not be inferred or persisted as sensitive browser state.

## Historical Analysis Requirements

The historical-analysis page must use a clear configure → processing → results flow.

Before submission, show:

- Selected market
- Fixed preset and version
- UTC date range
- Data requirements
- Entry timing
- Holding period
- Fees
- Slippage
- Sizing
- Synthetic-short limitation where applicable
- Historical-simulation and financial-safety disclosures

Results must present:

- Sample and trade count
- Gross and net return
- Maximum drawdown
- Win rate
- Profit factor
- Equity progression
- Hypothetical trades
- Data coverage
- Dataset, preset, calculation, engine, and simulation versions
- All material assumptions and disclosures

Use existing server-provided values. Do not recalculate indicators or performance metrics in the browser. Charts require accessible textual or table alternatives. Undefined and zero-trade metrics must be explicit.

## Design-System Requirements

The application must have shared repository-owned primitives and patterns for:

- Buttons and action hierarchy
- Cards and metric cards
- Badges and lifecycle statuses
- Inputs, selects, switches, labels, and helper text
- Dialogs and responsive drawers
- Tabs and breadcrumbs
- Tables and responsive table containers
- Charts
- Tooltips and dropdown menus
- Loading skeletons
- Empty states
- Safe errors
- Confirmation flows
- Destructive actions
- Toast feedback where appropriate

Use a restrained neutral visual system. Avoid excessive gradients, neon cryptocurrency styling, fake glass effects, decorative motion, and multiple competing accent colors.

## Responsive and Accessibility Requirements

The redesign must support:

- Desktop, tablet, and mobile layouts
- Keyboard navigation
- Visible focus
- Skip navigation
- Correct landmarks and headings
- Accessible labels and descriptions
- Screen-reader announcements for asynchronous state
- Reduced-motion preferences
- Sufficient contrast in light and dark themes
- Accessible chart alternatives
- Responsive dialogs, drawers, tables, and navigation

Accessibility behavior must not be traded away for template appearance.

## Security and Privacy Requirements

- Preserve the existing opaque-cookie authentication and CSRF model.
- Preserve owner-scoped requests and responses.
- Do not expose internal user IDs, provider identifiers, secrets, raw errors, calculation state, or unsupported delivery details.
- Do not store session, CSRF, Telegram, event, report, or other sensitive data in browser storage.
- Theme preference and the existing non-sensitive browser-sound boolean may use their approved browser persistence boundaries.
- Do not add third-party analytics or external font/runtime dependencies without a separate approved decision.

## Technical Boundaries

This story changes frontend structure and presentation only.

It must preserve:

- Existing API contracts
- Existing hooks and clients unless safely reorganized
- Existing domain calculations
- Existing provider behavior
- Existing SSE behavior
- Existing notification semantics
- Existing historical-analysis assumptions and metrics
- Existing authentication and authorization

Backend changes require a separate approved story or issue unless a strictly necessary presentation-only endpoint gap is discovered and approved through the normal workflow.

## Out of Scope

- New markets, alert types, presets, notification channels, or analysis metrics
- Custom strategies or optimization
- Delivery-history feature
- Portfolio tracking or trading
- Public reports, exports, sharing, billing, teams, or RBAC
- Production deployment
- Automated browser/end-to-end testing
- Replacing the backend or authentication architecture
- Importing an unrelated complete admin product

## Acceptance Criteria

- [ ] The application uses the approved shadcn/ui `dashboard-01` direction and repository-owned components.
- [ ] Authenticated features are organized into clear Overview, Price Alerts, Preset Signals, Historical Analysis, and Telegram destinations.
- [ ] Desktop and mobile navigation are responsive and accessible.
- [ ] Existing user journeys remain behaviorally equivalent after migration.
- [ ] Loading, empty, pending, unavailable, stale-session, rate-limited, error, confirmation, and destructive states are consistently designed.
- [ ] Light and dark themes are coherent and accessible.
- [ ] Historical-analysis charts and tables use existing server data and preserve exact domain meaning.
- [ ] No fake template data, duplicate authentication, unrelated admin features, or unsupported claims remain.
- [ ] Sensitive data and browser-storage boundaries remain unchanged.
- [ ] Current-state frontend, product, architecture, security, accessibility, operations, observability, README, concerns, and continuity documentation remain synchronized.

## Implementation Issues

- #101 — Add shadcn dashboard design-system foundation
- #102 — Add responsive dashboard shell and overview
- #103 — Redesign price alerts, preset signals, and Telegram workflows
- #104 — Redesign historical analysis and complete responsive polish

Implementation order:

```text
#101 → #102 → #103 → #104
```

Each issue requires an explicitly approved technical solution comment before implementation.

## Verification Boundary

Planning approval does not authorize package installation, builds, tests, browser interaction, HTTP requests, providers, workers, linting, formatting checks, type checks, accessibility scanners, or other verification commands. Those remain subject to explicit maintainer direction.