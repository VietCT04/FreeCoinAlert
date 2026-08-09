import Link from "next/link";

import type { GuideArticle } from "../../../content/guides/types";
import { MarketingFooter } from "../marketing-footer";
import { MarketingHeader } from "../marketing-header";
import { BacktestCta } from "../seo/backtest-cta";
import {
  createBreadcrumbJsonLd,
  guideCanonicalUrl,
  GuideJsonLd,
} from "./guide-seo";
import { GuideToc } from "./guide-toc";
import { RelatedGuides } from "./related-guides";

type GuideLayoutProps = {
  article: GuideArticle;
  relatedGuides: readonly GuideArticle[];
};

function formatGuideDate(date: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "long",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));
}

export function GuideLayout({ article, relatedGuides }: GuideLayoutProps) {
  const canonicalPath = `/guides/${article.slug}`;
  const canonicalUrl = guideCanonicalUrl(canonicalPath);
  const breadcrumbJsonLd = createBreadcrumbJsonLd([
    { name: "FreeCoinAlert", path: "/" },
    { name: "Guides", path: "/guides" },
    { name: article.title, path: canonicalPath },
  ]);
  const articleJsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    "@id": `${canonicalUrl}#article`,
    headline: article.title,
    description: article.summary,
    datePublished: article.publishedAt,
    dateModified: article.updatedAt,
    author: { "@type": "Organization", name: article.author },
    publisher: { "@type": "Organization", name: article.author },
    mainEntityOfPage: canonicalUrl,
  };

  return (
    <>
      <GuideJsonLd value={breadcrumbJsonLd} />
      <GuideJsonLd value={articleJsonLd} />
      <div className="min-h-svh bg-background text-foreground">
        <MarketingHeader />
        <main className="px-5 py-8 sm:px-8 sm:py-12">
          <div className="mx-auto max-w-5xl">
            <nav aria-label="Breadcrumb" className="text-sm text-muted-foreground">
              <ol className="flex flex-wrap items-center gap-2">
                <li>
                  <Link className="hover:text-foreground" href="/">
                    FreeCoinAlert
                  </Link>
                </li>
                <li aria-hidden="true">/</li>
                <li>
                  <Link className="hover:text-foreground" href="/guides">
                    Guides
                  </Link>
                </li>
                <li aria-hidden="true">/</li>
                <li aria-current="page" className="text-foreground">
                  {article.title}
                </li>
              </ol>
            </nav>

            <article className="mt-8 max-w-4xl">
            <header>
              <p className="text-sm font-medium tracking-[0.16em] text-muted-foreground uppercase">
                FreeCoinAlert guide
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
                {article.title}
              </h1>
              <p className="mt-5 max-w-3xl text-lg leading-8 text-muted-foreground">
                {article.summary}
              </p>
              <p className="mt-4 text-sm text-muted-foreground">
                Updated {formatGuideDate(article.updatedAt)} · By {article.author}
              </p>
            </header>

            <div className="mt-8">
              <GuideToc sections={article.sections} />
            </div>

            <div className="prose-freecoin mt-10 max-w-3xl text-[1.05rem] leading-8">
              {article.body}
            </div>

            {article.historicalSimulation ? (
              <aside className="mt-10 rounded-xl border border-amber-500/40 bg-amber-500/10 p-5 text-sm leading-7 text-muted-foreground">
                Historical-analysis results are hypothetical simulations over stored
                candles. They are not financial advice, predictions, trade execution,
                or a guarantee of delivery or profit.
              </aside>
            ) : null}

            <BacktestCta
              body="Choose a supported market, timeframe, entry, and exit assumptions in the historical-analysis workspace. The result is a hypothetical simulation, not a forecast or trade instruction."
              heading="Test the idea with your own range"
            />
            <RelatedGuides
              guides={relatedGuides}
              landingRoutes={article.relatedLandingRoutes}
            />
            </article>
          </div>
        </main>
        <MarketingFooter />
      </div>
    </>
  );
}
