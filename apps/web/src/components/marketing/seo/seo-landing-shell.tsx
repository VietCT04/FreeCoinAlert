import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingHeader } from "@/components/marketing/marketing-header";
import type { SeoLandingPage } from "@/content/seo/landing-pages";
import { SITE_URL } from "@/lib/seo/site";
import { JsonLd } from "@/lib/seo/structured-data";

import { BacktestCta } from "./backtest-cta";
import { BreadcrumbNav } from "./breadcrumb-nav";
import { FeatureExample } from "./feature-example";
import { RelatedPages } from "./related-pages";

type SeoLandingShellProps = {
  page: SeoLandingPage;
};

function BreadcrumbJsonLd({ page }: SeoLandingShellProps) {
  const payload = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: new URL("/", SITE_URL).toString(),
      },
      {
        "@type": "ListItem",
        position: 2,
        name: page.title,
        item: new URL(page.path, SITE_URL).toString(),
      },
    ],
  };

  return <JsonLd data={payload} />;
}

export function SeoLandingShell({ page }: SeoLandingShellProps) {
  return (
    <div className="min-h-svh bg-background text-foreground">
      <MarketingHeader />
      <main>
        <div className="mx-auto max-w-6xl px-6 py-10 sm:px-8 sm:py-16">
          <BreadcrumbNav title={page.title} />

          <article className="space-y-16">
            <header className="max-w-4xl space-y-6">
              <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                {page.primaryIntent}
              </p>
              <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">{page.h1}</h1>
              <p className="max-w-3xl text-lg leading-8 text-muted-foreground sm:text-xl">
                {page.intro}
              </p>
            </header>

            {page.sections.map((section) => (
              <section
                aria-labelledby={`${page.slug}-${section.id}-heading`}
                className="grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]"
                key={section.id}
              >
                <div>
                  <h2
                    className="text-2xl font-semibold tracking-tight sm:text-3xl"
                    id={`${page.slug}-${section.id}-heading`}
                  >
                    {section.heading}
                  </h2>
                </div>
                <div className="space-y-5 text-base leading-7 text-muted-foreground">
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                  {section.bullets ? (
                    <ul className="list-disc space-y-2 pl-5">
                      {section.bullets.map((bullet) => (
                        <li key={bullet}>{bullet}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              </section>
            ))}

            {page.example ? (
              <section aria-labelledby={`${page.slug}-example-heading`} className="space-y-5">
                <div>
                  <h2
                    className="text-2xl font-semibold tracking-tight sm:text-3xl"
                    id={`${page.slug}-example-heading`}
                  >
                    {page.example.heading}
                  </h2>
                  <p className="mt-3 max-w-3xl leading-7 text-muted-foreground">
                    {page.example.intro}
                  </p>
                </div>
                <FeatureExample
                  label={page.example.label}
                  note={page.example.note}
                  rows={page.example.rows}
                />
              </section>
            ) : null}

            <section aria-labelledby={`${page.slug}-limits-heading`} className="space-y-5">
              <div>
                <h2
                  className="text-2xl font-semibold tracking-tight sm:text-3xl"
                  id={`${page.slug}-limits-heading`}
                >
                  Important limits
                </h2>
                <p className="mt-3 max-w-3xl leading-7 text-muted-foreground">
                  Historical reports are bounded, hypothetical simulations. These limits keep the
                  result tied to the documented data and execution assumptions.
                </p>
              </div>
              <ul className="grid gap-3 sm:grid-cols-2">
                {page.limitations.map((limitation) => (
                  <li
                    className="rounded-xl border bg-card p-4 leading-7 text-muted-foreground"
                    key={limitation}
                  >
                    {limitation}
                  </li>
                ))}
              </ul>
            </section>

            {page.faqs ? (
              <section aria-labelledby={`${page.slug}-faq-heading`} className="space-y-5">
                <h2
                  className="text-2xl font-semibold tracking-tight sm:text-3xl"
                  id={`${page.slug}-faq-heading`}
                >
                  Frequently asked questions
                </h2>
                <div className="divide-y rounded-2xl border bg-card px-5">
                  {page.faqs.map((faq) => (
                    <div className="py-5" key={faq.question}>
                      <h3 className="font-semibold text-foreground">{faq.question}</h3>
                      <p className="mt-2 leading-7 text-muted-foreground">{faq.answer}</p>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            <RelatedPages pages={page.relatedPages} />

            <BacktestCta body={page.cta.body} heading={page.cta.heading} />
          </article>
        </div>
      </main>
      <MarketingFooter />
      <BreadcrumbJsonLd page={page} />
    </div>
  );
}
