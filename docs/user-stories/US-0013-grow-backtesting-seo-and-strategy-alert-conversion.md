# US-0013: Grow Backtesting SEO and Strategy-Alert Conversion

## Status

Approved

## User Story

As a crypto trader searching for a way to test a trading strategy, I want to discover FreeCoinAlert through search, backtest an entry/exit strategy on historical crypto data, understand the result, and then monitor the same entry condition for a future alert, so that I can validate an idea before watching for it in the live market.

## Product Positioning

FreeCoinAlert is positioned primarily as a crypto strategy backtesting and monitoring product rather than a generic price-alert website.

The core acquisition and conversion story is:

```text
Search for a crypto strategy test
        ↓
Define entry and exit rules
        ↓
Backtest on historical data
        ↓
Inspect performance, trades, and assumptions
        ↓
Monitor the same entry condition
        ↓
Receive a Telegram alert when the entry signal occurs again
```

Primary public message:

```text
Free Crypto Strategy Backtesting & Alerts

Backtest it.
Understand it.
Get alerted when it happens.
```

The product must never imply that a historical result guarantees future performance or that creating an entry alert creates a live trade.

## Search Objective

The business objective is to earn strong organic visibility for crypto backtesting and strategy-testing searches.

Primary search-intent cluster:

```text
crypto backtest
crypto backtesting
free crypto backtesting
crypto backtesting tool
crypto strategy tester
crypto strategy backtest
backtest crypto strategy
test crypto strategy
trading strategy tester crypto
bitcoin backtest
bitcoin strategy tester
```

Indicator and strategy clusters:

```text
RSI backtest
RSI strategy backtest
RSI crypto strategy
RSI trading strategy tester
SMA backtest
moving average backtest crypto
SMA crossover backtest
crypto SMA strategy
take profit stop loss backtest
crypto TP SL backtest
backtest entry exit strategy
crypto trading strategy test
```

Monitoring/conversion cluster:

```text
crypto strategy alert
RSI alert
RSI crossing alert
crypto entry signal alert
Telegram trading strategy alert
alert when RSI crosses 30
```

Terms such as `cointest` or other emerging variants may be observed in Search Console after launch, but the product must not create thin pages for unproven keyword variants.

## Ranking Goal

The ongoing product objective is:

```text
Top 5 organic results for selected primary backtesting/strategy-testing queries.
Top 10 organic results for important secondary queries.
```

This is a measured business outcome, not an engineering guarantee or acceptance criterion. Search engines determine ranking using signals outside the application's control.

Engineering acceptance is limited to producing crawlable, fast, semantic, useful, technically correct public pages, a strong product conversion funnel, and measurable search performance.

## Public Information Architecture

The initial public route structure is:

```text
/
    Crypto Strategy Backtester

/crypto-backtesting
    Broad crypto backtesting intent

/crypto-strategy-tester
    Strategy construction/testing intent

/bitcoin-backtest
    Bitcoin backtesting intent

/rsi-backtest
    RSI strategy-testing intent

/sma-backtest
    SMA / moving-average backtesting intent

/tp-sl-backtest
    Take-profit / stop-loss testing intent

/strategy-alerts
    Backtest-to-entry-monitoring intent

/guides/
    how-to-backtest-crypto-strategy
    rsi-backtesting
    rsi-cross-below-30-strategy
    sma-crossover-backtesting
    crypto-take-profit-stop-loss
    backtesting-vs-forward-testing
    backtesting-fees-slippage
    common-backtesting-mistakes
```

Authenticated/user-specific application routes remain separate from the public acquisition surface and must not be accidentally indexed.

## Homepage Requirements

The root page becomes a substantial public landing page rather than only a small authentication gateway.

The homepage must communicate the actual product clearly, for example:

```text
Backtest Crypto Strategies for Free

Test RSI, moving-average, and entry/exit strategies against historical crypto data.
Set take profit, stop loss, indicator exits, and time-based exits; inspect hypothetical trades and performance; then monitor the strategy's entry signal.
```

The homepage should include useful sections such as:

- strategy-builder example;
- supported entry concepts;
- take-profit, stop-loss, indicator, and time-based exits;
- historical performance/report explanation;
- execution assumptions and limitations;
- supported markets/timeframes based on actual current product behavior;
- the backtest-to-alert workflow;
- FAQ;
- sign-up/sign-in/dashboard/backtest calls to action.

The page must not display fabricated historical returns, fabricated users, fabricated testimonials, or unsupported strategy features.

## Landing-Page Requirements

Each high-intent public route must serve a distinct user intent rather than being a keyword synonym page.

Examples:

### `/crypto-backtesting`

Explain the complete backtesting workflow, historical data, execution assumptions, metrics, and limitations.

### `/crypto-strategy-tester`

Focus on constructing a complete strategy from entry plus exit rules and testing that configuration historically.

### `/bitcoin-backtest`

Use truthful Bitcoin-focused examples based on supported BTC market/timeframe capabilities.

### `/rsi-backtest`

Explain RSI entry/exit semantics, RSI crossing behavior, and actual supported RSI strategy examples.

### `/sma-backtest`

Explain supported SMA crossover behavior and historical testing.

### `/tp-sl-backtest`

Explain take-profit/stop-loss testing, gap behavior, candle OHLC limitations, and conservative same-candle ambiguity rules where applicable.

### `/strategy-alerts`

Explain the bridge from a completed historical backtest to monitoring the same entry condition in the live signal system.

Every page must have unique useful content, title, description, canonical URL, H1, internal links, and relevant CTA.

## Backtest-to-Alert Conversion

An eligible completed historical strategy report should offer:

```text
Monitor this entry
```

Example historical strategy:

```text
BTCUSDT · 1H
Entry: RSI(14) crosses below 30
Take profit: +6%
Stop loss: -3%
Maximum holding: 7 candles
```

The conversion action monitors only:

```text
RSI(14) crosses below 30 on BTCUSDT 1H
```

The user-facing meaning must remain explicit:

- the backtest exit rules describe historical hypothetical simulation;
- the live alert monitors the entry condition;
- creating the alert does not create a live position;
- TP/SL/time exits are not automatically live-tracked by this story;
- no trading or order execution occurs.

The implementation should reuse existing preset signal/subscription and Telegram behavior wherever the entry semantics match rather than creating a duplicate live strategy engine.

## Educational Content Cluster

FreeCoinAlert should publish a bounded set of original, useful educational pages that answer real backtesting questions and lead naturally to the product.

Initial topics:

- how to backtest a crypto strategy;
- RSI backtesting;
- RSI crossing below 30 strategy mechanics;
- SMA crossover backtesting;
- take-profit and stop-loss backtesting;
- backtesting versus forward testing;
- fees and slippage in a backtest;
- common backtesting mistakes.

Content must explain actual concepts, assumptions, limitations, and examples rather than serving as keyword filler.

No mass-generated symbol pages, indicator permutations, copied competitor content, unsupported claims, or automated low-value content are introduced by this story.

## Technical SEO Requirements

Public pages must have a consistent technical SEO foundation:

- production-owned site URL;
- route-specific title and description;
- canonical URL;
- Open Graph metadata;
- social-card metadata;
- sitemap containing intended public canonical routes;
- robots policy that allows intended public pages and protects private/user-specific surfaces;
- server-rendered semantic primary content;
- one clear primary H1 per landing/article page;
- logical heading hierarchy;
- descriptive internal links;
- accessible images/examples;
- no duplicate canonical variants;
- no local/E2E hostnames in production metadata;
- safe structured data only when it truthfully describes visible page content and product behavior.

Authenticated dashboards, account-specific results, private runs, private alerts, and user-specific state must not become search landing pages.

## Search and Content Quality Requirements

SEO work must remain people-first and product-truthful.

The implementation must not:

- guarantee search ranking;
- keyword-stuff titles or copy;
- create doorway pages for near-identical query variants;
- claim unsupported markets, exchanges, indicators, strategies, or execution features;
- make profitability guarantees;
- present historical results as predictions;
- generate fake reviews/testimonials;
- expose private data for indexing;
- sacrifice accessibility or application security for SEO.

## Performance Requirements

Public acquisition pages should remain lightweight and server-rendered where practical.

They should target good Core Web Vitals and avoid requiring heavy authenticated application bundles merely to render public explanatory content.

Performance improvements must not weaken application correctness, accessibility, or security.

## Measurement Requirements

Google Search Console is the primary external measurement surface for this story.

Track over time:

- search queries;
- landing pages;
- impressions;
- clicks;
- click-through rate;
- average search position;
- indexed-page coverage;
- Core Web Vitals/search experience signals where available.

Primary query clusters are initial hypotheses. Real Search Console impressions and clicks should be used to refine future page/query priorities rather than permanently hard-coding the initial keyword list as truth.

Search Console verification must not require Google account credentials to be stored by the FreeCoinAlert runtime.

## SEO Regression Requirements

Use the existing test architecture where appropriate to protect important public-search behavior.

Regression coverage should verify at least:

- intended public routes return usable public content;
- title and description exist;
- canonical URL is correct;
- intended public routes are indexable;
- private/authenticated routes are not intentionally exposed for indexing;
- public pages have a clear H1;
- sitemap contains intended routes and excludes private routes;
- robots rules do not accidentally block intended pages;
- production canonical URLs cannot resolve to local/E2E hosts;
- bounded public internal links do not silently break.

## Security and Privacy Requirements

- Preserve opaque-cookie authentication and CSRF behavior.
- Preserve owner-scoped runs, reports, alerts, subscriptions, and Telegram state.
- Do not expose authenticated API response data as static/public SEO content.
- Do not make user-specific historical reports publicly indexable.
- Search Console verification/configuration must not expose account credentials.
- No new browser persistence containing strategy/report data is required for SEO.

## Out of Scope

- Search-ranking guarantees
- Paid search advertising
- Backlink-buying or manipulation services
- Automated mass SEO-page generation
- Public user-generated strategy pages
- Public sharing of private historical reports
- New arbitrary strategy formulas solely for SEO content
- New markets/exchanges solely to target keywords
- Live TP/SL position monitoring
- Automated trading or order execution
- Financial advice or guaranteed strategy recommendations
- General crypto news publishing

## Acceptance Criteria

- [ ] FreeCoinAlert's public positioning is primarily crypto strategy backtesting plus entry-signal monitoring rather than generic coin alerts.
- [ ] `/` is a substantial public, server-rendered backtesting-focused landing page.
- [ ] Public technical SEO includes route-specific metadata, canonical URLs, robots policy, sitemap, and social metadata.
- [ ] Private/authenticated/user-specific application routes are kept outside the intended search-index surface.
- [ ] High-intent public pages exist for broad backtesting, strategy testing, Bitcoin backtesting, RSI, SMA, TP/SL, and strategy alerts, with distinct useful content.
- [ ] Educational guides answer distinct backtesting questions without keyword stuffing or duplicated thin content.
- [ ] Public pages explain only behavior actually supported by FreeCoinAlert.
- [ ] Eligible completed historical reports can lead the user to monitor the same entry condition using existing live signal/subscription semantics where possible.
- [ ] The backtest-to-alert flow clearly states that only the entry condition is monitored; historical exit rules are not live positions or orders.
- [ ] Search Console setup and SEO measurement are documented without storing Google account credentials in the application.
- [ ] SEO regression checks protect canonical/index/sitemap/robots/H1/private-route boundaries.
- [ ] No fabricated performance, search-rank, testimonial, or profitability claims are introduced.
- [ ] Existing authentication, CSRF, ownership, backtesting, signal, Telegram, accessibility, and security guarantees remain intact.
- [ ] Current-state product, API, architecture, backtesting, strategy, security, testing, E2E, operations, concerns, README, and continuity documentation remain synchronized during implementation.

## Product Success Metric

After launch, the product aims for top-five organic search visibility on selected primary backtesting/strategy-testing queries and top-ten visibility on important secondary queries.

This target is reviewed through Search Console over time and is not treated as a condition that engineering can guarantee at merge time.

## Implementation Issues

- #141 — Add technical SEO foundation for public backtesting pages
- #142 — Turn the public homepage into a crypto strategy backtesting landing page
- #143 — Add high-intent crypto backtesting and strategy-testing landing pages
- #144 — Convert a backtested entry rule into a live strategy alert
- #145 — Add educational crypto backtesting and strategy-testing content cluster
- #146 — Add Search Console measurement and SEO regression checks

Recommended implementation order:

```text
#141
  ↓
#142
  ↓
#143
  ↓
#144
  ↓
#145
  ↓
#146
```

#144 may proceed in parallel with content work once its backtesting and live-subscription prerequisites are stable, but the final story should be evaluated as one coherent search-to-product funnel.

Each implementation issue requires an explicitly approved technical solution comment before implementation.

## Verification Boundary

Planning approval does not authorize package installation, builds, tests, browser interaction, Playwright, E2E execution, Lighthouse, Search Console verification, sitemap submission, production indexing requests, external provider calls, linting, formatting checks, type checks, accessibility scans, documentation generators, or other verification commands. Those remain subject to explicit maintainer direction.