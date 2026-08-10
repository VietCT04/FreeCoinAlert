# US-0015: Redesign the Public Homepage Around the Backtesting Product

## Status

Approved

## User Story

As a visitor evaluating FreeCoinAlert, I want the public homepage to immediately explain and show the backtesting product without a crowded keyword-heavy navigation or repeated sections, so that I can understand the product quickly, see what makes it useful, and start backtesting with confidence.

## Context

The current public homepage has a technically sound SEO foundation but weak product hierarchy.

The global header currently mixes several different kinds of destinations at the same visual level:

```text
product/navigation destinations
+ SEO keyword landing pages
+ homepage anchor links
+ authentication actions
```

This produces an overcrowded first impression and makes related concepts such as crypto backtesting, strategy testing, RSI backtesting, workflow explanation, supported inputs, and FAQ compete for attention.

The homepage body also repeats the same core narrative across multiple sections:

```text
hero workflow
→ How it works
→ Example strategy
→ What you can test
→ Backtesting assumptions
→ Understand the result
→ Backtest-to-alert explanation
→ supported-market context
→ FAQ
→ final CTA
```

The approved redesign keeps the existing public SEO architecture but reorganizes the visible experience around the actual product.

## Competitive Benchmark Findings

The redesign direction is informed by current crypto/trading/backtesting product landing pages including TradingView, Coinrule, Cryptohopper, Bitsgap, and 3Commas.

The useful common patterns are:

- Primary navigation groups major product areas rather than exposing one link per SEO keyword or feature.
- Dedicated SEO/backtesting pages remain separate from the main human navigation.
- The first viewport uses one strong value proposition and one dominant CTA.
- Strong landing pages show the actual product or a realistic product representation near the hero instead of relying only on prose.
- Product stories progress from value proposition to product proof to workflow/result to conversion.
- Detailed documentation/resources are pushed into contextual links, guides, disclosure sections, or grouped footer navigation.
- Strategy/result visuals are more persuasive than repeated feature-card lists, but performance claims must remain truthful and clearly contextualized.

FreeCoinAlert should adopt the information-design strengths of those products without copying their visual identity or adopting aggressive automated-trading/ROI marketing.

## Product Narrative

The homepage should be organized around one concise product story:

```text
Backtest it.
Understand it.
Get alerted when it happens again.
```

A more direct hero expression may be:

```text
Backtest a crypto strategy before you trust it.

Define the rules. Test them on historical crypto data.
Get alerted when the entry appears again.
```

The exact final copy is owned by the implementation technical solution, but it must stay concise and avoid visible keyword stuffing.

## Primary Navigation

The public desktop header should be reduced to the major user destinations, approximately:

```text
FreeCoinAlert     Backtest     Alerts     Guides     Sign in     Start free
```

Requirements:

- `Start free` is the single visually dominant primary CTA.
- `Sign in` remains secondary/plain.
- SEO-specific landing pages such as RSI Backtest or Crypto Strategy Tester do not occupy the main header.
- Homepage anchors such as How it works, What you can test, and FAQ do not occupy the main desktop header.
- Mobile navigation is compact and accessible rather than horizontally overflowing.
- Sticky/backdrop-blur behavior may be used subtly to maintain orientation without becoming visually noisy.

## SEO and Internal-Link Principle

Removing an SEO landing page from the primary header does not mean deleting, deindexing, or orphaning it.

Important public routes remain discoverable through a logical link graph using:

- contextual homepage links;
- related landing pages;
- relevant guides;
- grouped footer navigation;
- sitemap/public route registry.

The visible public navigation should serve humans first while preserving a crawlable and semantically logical site structure.

## Footer Information Architecture

Replace the current flat horizontal link wall with grouped columns, approximately:

```text
Product
- Backtester
- Strategy Alerts

Learn
- Guides
- How backtesting works
- FAQ

Popular backtests
- RSI Backtest
- SMA Backtest
- TP/SL Backtest
- Bitcoin Backtest
```

The final labels/routes must reflect the actual public route registry.

## Hero Requirements

The current hero text plus text-only workflow card should be replaced with a product-first composition.

The first viewport should contain:

```text
clear H1
short supporting copy
primary CTA
secondary action
small factual trust/safety line
realistic Historical Analysis product preview
```

The product preview should resemble the real FreeCoinAlert backtesting experience rather than a generic marketing illustration.

It may show a controlled example strategy such as:

```text
XRPUSDT · 1H
RSI(14) crosses below 30
TP +6%
SL -3%
max holding 7 candles
chart / entry marker
report metrics
```

Do not fabricate impressive historical returns or other performance claims.

Any numerical performance example must be derived from a deterministic known fixture or otherwise clearly neutral/non-performance content.

## Hero Motion

Subtle motion may be used to make the product understandable and visually distinctive.

A possible sequence is:

```text
indicator approaches threshold
→ entry signal appears
→ price/chart progresses
→ report state appears
→ monitor-entry action appears
```

Motion requirements:

- must remain subtle;
- no flashing/casino-style treatment;
- static state remains fully understandable;
- respect `prefers-reduced-motion`;
- prefer CSS/Tailwind/small React behavior before adding a new animation dependency;
- animation is presentation only and must not be required for semantic content or interaction.

## Product-Proof Strip

Directly beneath the hero, show a compact row of truthful product facts using only currently shipped capabilities.

Examples may include:

```text
Binance Spot
RSI & SMA
TP / SL
fees modeled
no order execution
```

Do not advertise the upcoming two-year historical-data capability until the relevant implementation has actually shipped.

## Homepage Information Architecture

The body should be consolidated toward approximately:

```text
1. Hero + product preview
2. Compact factual proof strip
3. Build → Backtest → Alert workflow
4. Product/report showcase
5. Why FreeCoinAlert / differentiation
6. Methodology progressive disclosure
7. FAQ
8. Final CTA
```

The exact component count may differ, but repeated concepts must be merged rather than retained under slightly different headings.

## Build → Backtest → Alert

Use one strong visual workflow instead of repeating the workflow in multiple sections.

Conceptually:

```text
Define rules
    ↓
Backtest historical data
    ↓
Understand the report
    ↓
Monitor the supported entry condition
```

The page must clearly communicate:

- live monitoring watches the supported entry condition;
- historical exits do not become live positions/orders;
- FreeCoinAlert does not place exchange orders.

## Product / Report Showcase

Replace several text-card sections with a more visual product explanation.

A strategy configuration may show:

```text
Market
Timeframe
Entry rule
Take profit
Stop loss
Indicator exit
Maximum holding
Entry timing
Fees/slippage
```

Beside it, show what the report returns where supported:

```text
trades
entry / exit markers
net return
maximum drawdown
win rate
profit factor
equity progression
exit reasons
```

This should communicate supported inputs, execution assumptions, and report outputs in one product-focused section instead of three separate card grids.

## Differentiation

FreeCoinAlert should not position itself as another automated trading-bot platform.

The approved differentiation is approximately:

```text
Test before monitoring
Transparent execution assumptions
No exchange trading permissions / no order execution
```

The homepage should communicate these benefits positively without attacking or naming competitors.

## Methodology Progressive Disclosure

Detailed backtesting assumptions are valuable but should not dominate the marketing page.

Move detailed execution semantics into an accessible progressive-disclosure section, for example:

```text
How does the backtest work?
```

which can expose details such as:

```text
signal confirmation timing
entry timing
fees
slippage
position sizing
same-candle priority
overlapping-signal behavior
end-of-range behavior
```

Important semantic content must remain present/crawlable and accessible.

## FAQ and Final CTA

Keep only high-value questions that resolve genuine product uncertainty.

Avoid restating the entire product pitch again in the FAQ.

The page ends with one clear final conversion section rather than multiple repeated CTA narratives.

## Visual Design Direction

Use stronger hierarchy with fewer equal-weight bordered cards.

Approved visual techniques include:

- stronger whitespace and section rhythm;
- subtle alternating section surfaces;
- restrained card shadows/depth;
- faint grid or radial hero background treatment;
- subtle hover lift for meaningful interactive cards;
- small CTA arrow movement;
- sticky translucent header treatment;
- lightweight chart/signal animation;
- rounded major product surfaces;
- responsive stacking on mobile.

Avoid:

- excessive gradients;
- flashing financial/casino aesthetics;
- continuous distracting animation;
- fake testimonials or social proof;
- fake user counts;
- fake returns;
- fake rankings;
- promises of profit.

## Component Direction

Move the homepage away from one large monolithic `page.tsx` toward composable marketing sections, approximately:

```text
components/marketing/homepage/
  hero.tsx
  hero-product-demo.tsx
  proof-strip.tsx
  product-flow.tsx
  report-preview.tsx
  differentiation.tsx
  methodology-disclosure.tsx
  homepage-faq.tsx
  final-cta.tsx
```

The exact component boundaries are owned by the approved technical solution and should avoid unnecessary abstraction.

## Social / Reddit Sharing

The redesigned homepage should have a product-oriented Open Graph/Twitter image designed to remain recognizable when shared on Reddit, Discord, Telegram, and other link-preview surfaces.

Target composition:

```text
1200 × 630
FreeCoinAlert
Backtest a crypto strategy before you trust it.
realistic product/chart/report visual
Backtest → Understand → Get alerted
```

Requirements:

- readable at small preview sizes;
- important content inside safe crop margins;
- no fabricated performance claims;
- use current Next.js metadata/image conventions where practical;
- do not add an SEO package solely for this feature.

## Accessibility and Performance

- Preserve semantic heading hierarchy.
- Keep primary navigation keyboard accessible.
- Mobile menu must have correct focus/expanded behavior.
- Motion respects reduced-motion preferences.
- Do not require animation for content comprehension.
- Avoid unnecessary client-side code in static marketing content.
- Avoid adding an animation library unless the technical solution demonstrates clear need.
- Keep image/social-preview implementation compatible with the current Next.js App Router stack.

## Historical / Product Truthfulness

The homepage must reflect only shipped behavior.

In particular:

- do not advertise two years of backtesting before US-0014 implementation ships;
- do not imply arbitrary strategy code support;
- do not imply live TP/SL/order management when live monitoring only watches supported entry conditions;
- do not imply exchange account connectivity for trading;
- do not turn hypothetical results into predictive claims.

## Out of Scope

- New strategy types solely for the redesign
- New exchange integrations
- Live order execution
- Search-ranking guarantees
- New SEO landing pages solely to fill navigation
- A new general-purpose animation framework
- A full visual-regression platform for the application
- Changing historical-analysis execution semantics

## Acceptance Criteria

- [ ] Desktop primary navigation is reduced to a small product-oriented set of destinations.
- [ ] Sign in is secondary and one Start free action is visually primary.
- [ ] Public mobile navigation is accessible and does not horizontally overflow.
- [ ] Existing important SEO routes remain crawlable even after leaving the primary header.
- [ ] Footer links are logically grouped instead of presented as a flat link wall.
- [ ] The hero immediately communicates backtesting plus entry-signal monitoring.
- [ ] The hero includes a realistic product representation rather than a text-only workflow card.
- [ ] Any animation is subtle, optional, and reduced-motion safe.
- [ ] The hero/product proof uses only currently shipped capabilities.
- [ ] Repeated homepage sections are consolidated into one coherent product story.
- [ ] Supported inputs, execution assumptions, and report outputs are explained visually with less repeated prose.
- [ ] The page clearly distinguishes historical strategy exits from live entry-signal monitoring.
- [ ] The page clearly states that FreeCoinAlert does not place orders.
- [ ] Detailed methodology remains available through accessible progressive disclosure.
- [ ] Example performance data is truthful/deterministic and never fabricated for marketing.
- [ ] Homepage SEO title/description/canonical intent remains clear without keyword-heavy visible navigation.
- [ ] A 1200×630 product-oriented Open Graph/Twitter preview is provided.
- [ ] Social preview content remains readable and truthful for Reddit/social sharing.
- [ ] Relevant SEO/mobile/accessibility regression coverage is added without brittle ranking/pixel assertions.
- [ ] Existing private/dashboard routes remain excluded from public navigation and sitemap.
- [ ] No new animation/SEO dependency is added unless explicitly justified in the technical solution.

## Implementation Issues

- #161 — Simplify public navigation and footer information architecture
- #162 — Redesign homepage hero with product-focused animated preview
- #163 — Consolidate homepage into a focused backtest-to-alert product story
- #164 — Refresh homepage social preview and homepage regression coverage

Recommended implementation order:

```text
#161 → #162 → #163 → #164
```

Each issue requires an explicitly approved technical solution comment before implementation.

## Verification Boundary

Planning approval does not authorize builds, tests, browser interaction, Playwright/E2E, services, package installation, linting, formatting checks, type checks, external social-preview validators, screenshots, or other verification commands. Those remain subject to explicit maintainer direction.
