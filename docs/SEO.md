# Search and Public SEO

## Purpose and status

This document owns the public search-discovery contract and the maintainer's
external Search Console workflow. The application provides metadata, canonical
URLs, robots, sitemap, truthful structured data, and bounded public routes. It
does not promise search ranking or connect runtime code to Google Search
Console.

Availability: Implemented  
Verification: Unverified until a maintainer-requested public-route and SEO E2E
pass is run.

## Public route boundary

The web app keeps one bounded `PUBLIC_SEO_ROUTES` registry in
`apps/web/src/lib/seo/routes.ts`. It currently contains the public homepage,
seven strategy/backtesting landing pages, the guides hub, and eight guides.
The sitemap is generated only from that registry when indexing is enabled.

The registry must never contain sign-in/sign-up pages, dashboard routes,
owner-specific resources, API URLs, query-string variants, E2E/private pages,
or generated symbol/timeframe permutations. Every registered route owns its
visible H1, title, description, canonical, and public content. Public pages
use server-rendered copy and do not call authenticated APIs to produce SEO
content.

Private pages expose `noindex, nofollow` metadata. This is the privacy/indexing
boundary for `/sign-in`, `/sign-up`, `/dashboard`, `/price-alerts`,
`/preset-signals`, `/historical-analysis`, and `/telegram`; robots exclusion is
not used as a substitute for page-level `noindex`.

## Deployment configuration

The web process reads these server-owned settings:

| Setting | Default | Contract |
| --- | --- | --- |
| `SITE_URL` | `http://localhost:3000` in development only | Absolute `http`/`https` origin with no path, query, fragment, username, or password. Production requires `https` and a public hostname. |
| `SEO_INDEXING_ENABLED` | `false` | Public metadata and sitemap indexing are opt-in. Production must explicitly set `true`. |
| `GOOGLE_SITE_VERIFICATION` | empty | Optional URL-prefix verification token. Empty means no verification meta tag. |

`SITE_URL` is not a secret, but it remains server-owned configuration and is
never exposed as a `NEXT_PUBLIC_` value. Local and preview environments keep
indexing disabled. The isolated E2E web service explicitly uses its internal
`.test` origin and sets indexing enabled because that origin is not publicly
routable.

When indexing is enabled, `robots.txt` allows public crawling and advertises
`SITE_URL/sitemap.xml`. When disabled, it disallows `/` and advertises no
sitemap; the implementation keeps `/_next/` available to crawlers when the
disabled rule is rendered. The sitemap has no generated `lastmod`, priority,
or change-frequency values.

## Metadata and structured data

`createPublicMetadata()` centralizes unique titles, descriptions, exact
canonical paths, Open Graph, Twitter `summary_large_image`, and the current
index/follow policy. Open Graph and Twitter use the deterministic Next-native
`/opengraph-image` route, which returns a 1200×630 PNG based on the shared
server-safe marketing example; it does not call an API, database, provider, or
browser-only chart library. The root layout owns `metadataBase`, application
name, the default title/template, site description, social image, optional
Google verification, and the same indexing policy, but it does not own a
canonical that child routes could inherit incorrectly.

The root page publishes one truthful `WebSite` JSON-LD object. Landing and
guide pages publish `BreadcrumbList` only when the visible breadcrumb exists;
guide articles additionally publish `Article` with their maintained
publication/update dates and `FreeCoinAlert` as the publisher. JSON-LD escapes
serialized `<` characters before insertion. The application does not publish
reviews, ratings, `AggregateRating`, `SoftwareApplication` rich-result claims,
FAQ rich-result markup, financial-performance markup, or hidden structured data.

## Search Console setup

Search Console is an external maintainer tool. The application does not store
Google credentials, call Search Console APIs, schedule rank downloads, or add
analytics scripts merely for SEO.

For a production deployment:

1. Prefer a Search Console Domain property verified through DNS when the
   maintainer controls DNS; it covers protocol and subdomain variants.
2. Otherwise set `GOOGLE_SITE_VERIFICATION` for URL-prefix HTML meta
   verification, deploy it, and complete verification in Search Console.
3. Open Search Console → Sitemaps and submit
   `<production origin>/sitemap.xml`.
4. Inspect `/` and the highest-priority landing pages.
5. Confirm Google's selected canonical matches the intended canonical.
6. Review Page indexing after Google has had time to recrawl the deployment.
7. Review Core Web Vitals, manual actions, and security issues.

The token is configuration, not an authentication credential, but it must stay
outside source control and logs. A missing token does not make the application
fail.

## Query-cluster measurement

The following are initial measurement hypotheses, not ranking promises or
automatic page-generation inputs:

| Cluster | Example queries |
| --- | --- |
| Backtesting core | crypto backtest; crypto backtesting; free crypto backtesting; crypto backtesting tool |
| Strategy testing | crypto strategy tester; backtest crypto strategy; test crypto strategy; crypto strategy backtest |
| Bitcoin | bitcoin backtest; bitcoin strategy tester |
| RSI | RSI backtest; RSI strategy backtest; RSI crypto strategy |
| SMA | SMA backtest; SMA crossover backtest; moving average backtest crypto |
| Exit rules | TP SL backtest; take profit stop loss backtest; backtest entry exit strategy |
| Monitoring | crypto strategy alert; RSI alert; entry signal alert; Telegram strategy alert |

After impressions exist, refine these clusters from the actual Search Console
query report. Do not create a new page for every query variation.

For each 28-day window, compare with the previous 28 days:

- impressions, clicks, CTR, and average position;
- queries by cluster and landing page;
- indexed canonical pages and Page indexing issues;
- Core Web Vitals status; and
- manual actions and security issues when present.

Top-five ranking is a product objective, not an acceptance test. Do not claim
it from a personalized browser search or from a query with no meaningful
impressions; Search Console is the measurement source.

Operational Core Web Vitals targets are LCP ≤ 2.5 seconds, INP ≤ 200 ms, and
CLS ≤ 0.1. Field data from Search Console/CrUX is the outcome source; Docker
E2E timing is not a field-performance measurement.

## Regression coverage

`apps/e2e/specs/seo-public.spec.ts` uses the existing Playwright workspace and
the source `PUBLIC_SEO_ROUTES` registry. It covers public page loading, one
visible H1, unique title/description, canonical and social metadata, the
homepage's 1200×630 PNG route and PNG signature, desktop marketing navigation,
required contextual acquisition links, reduced-motion content visibility,
sitemap equality/uniqueness, robots behavior, private-route noindex, bounded
internal links, and truthful JSON-LD. The companion
`apps/e2e/specs/seo-public.mobile.spec.ts` covers the public mobile Sheet,
focus return, product preview visibility, and horizontal-overflow boundary.
These specifications do not attempt to reproduce Google's SERP rewriting,
social-platform caching/cropping, or Rich Results Test.

The E2E environment sets `SEO_INDEXING_ENABLED=true` only for the isolated
`.test` web origin. The normal local/preview default remains `false`. The
route/action matrix is [E2E_COVERAGE.md](E2E_COVERAGE.md), and the general
verification boundary is [TESTING.md](TESTING.md).

## Maintainer release checklist

- Set a production `SITE_URL` and confirm it has no path or credentials.
- Keep `SEO_INDEXING_ENABLED=false` until the intended production origin is
  deployed; then explicitly opt in.
- Configure verification outside source control if URL-prefix verification is
  selected.
- Review public route metadata, canonical uniqueness, sitemap, robots, private
  noindex behavior, and `/opengraph-image` response dimensions/content type.
- Submit the sitemap and inspect representative URLs in Search Console.
- Review indexing, queries, Core Web Vitals, manual actions, and security
  issues during the 28-day measurement cycle.
