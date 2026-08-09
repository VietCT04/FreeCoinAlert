import type { Metadata } from "next";
import Link from "next/link";

import { BacktestCta } from "../../components/marketing/seo/backtest-cta";
import { MarketingFooter } from "../../components/marketing/marketing-footer";
import { MarketingHeader } from "../../components/marketing/marketing-header";
import {
  createBreadcrumbJsonLd,
  GuideJsonLd,
} from "../../components/marketing/guides/guide-seo";
import { GUIDES } from "../../content/guides/registry";
import { createPublicMetadata } from "../../lib/seo/metadata";

export const metadata: Metadata = createPublicMetadata({
  title: "Crypto Backtesting Guides",
  description:
    "Plain-language guides to crypto backtesting, RSI and SMA entries, TP/SL assumptions, fees, forward testing, and common mistakes.",
  canonicalPath: "/guides",
});

export default function GuidesPage() {
  const breadcrumbJsonLd = createBreadcrumbJsonLd([
    { name: "FreeCoinAlert", path: "/" },
    { name: "Guides", path: "/guides" },
  ]);

  return (
    <>
      <GuideJsonLd value={breadcrumbJsonLd} />
      <div className="min-h-svh bg-background text-foreground">
        <MarketingHeader />
        <main className="px-5 py-8 sm:px-8 sm:py-12">
          <div className="mx-auto max-w-5xl">
          <nav aria-label="Breadcrumb" className="text-sm text-muted-foreground">
            <ol className="flex items-center gap-2">
              <li>
                <Link className="hover:text-foreground" href="/">
                  FreeCoinAlert
                </Link>
              </li>
              <li aria-hidden="true">/</li>
              <li aria-current="page" className="text-foreground">
                Guides
              </li>
            </ol>
          </nav>

          <header className="mt-8 max-w-3xl">
            <p className="text-sm font-medium tracking-[0.16em] text-muted-foreground uppercase">
              FreeCoinAlert guides
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
              Crypto backtesting, explained clearly
            </h1>
            <p className="mt-5 text-lg leading-8 text-muted-foreground">
              Learn how to define a historical question, inspect hypothetical
              results, understand execution assumptions, and distinguish future
              entry alerts from trade execution.
            </p>
          </header>

          <section aria-labelledby="guide-list" className="mt-10">
            <h2 id="guide-list" className="text-2xl font-semibold tracking-tight">
              Start with a guide
            </h2>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {GUIDES.map((guide) => (
                <Link
                  className="rounded-2xl border bg-card p-6 shadow-sm transition-colors hover:bg-muted/30"
                  href={`/guides/${guide.slug}`}
                  key={guide.slug}
                >
                  <h3 className="text-xl font-semibold tracking-tight">
                    {guide.title}
                  </h3>
                  <p className="mt-3 leading-7 text-muted-foreground">
                    {guide.summary}
                  </p>
                  <span className="mt-4 inline-block text-sm font-medium">
                    Read guide →
                  </span>
                </Link>
              ))}
            </div>
          </section>

          <BacktestCta
            body="Choose a supported market, timeframe, entry, and exit assumptions in the historical-analysis workspace. The result is a hypothetical simulation, not a forecast or trade instruction."
            heading="Start with a historical question"
          />
          </div>
        </main>
        <MarketingFooter />
      </div>
    </>
  );
}
