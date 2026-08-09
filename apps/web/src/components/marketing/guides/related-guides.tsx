import Link from "next/link";

import type { GuideArticle, GuideLink } from "../../../content/guides/types";

type RelatedGuidesProps = {
  guides: readonly GuideArticle[];
  landingRoutes: readonly GuideLink[];
};

export function RelatedGuides({ guides, landingRoutes }: RelatedGuidesProps) {
  if (guides.length === 0 && landingRoutes.length === 0) {
    return null;
  }

  return (
    <section aria-labelledby="related-reading" className="mt-12 border-t pt-8">
      <h2 id="related-reading" className="text-2xl font-semibold tracking-tight">
        Related reading
      </h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {guides.map((guide) => (
          <Link
            className="rounded-xl border p-4 transition-colors hover:bg-muted/50"
            href={`/guides/${guide.slug}`}
            key={guide.slug}
          >
            <span className="font-medium">{guide.title}</span>
            <span className="mt-1 block text-sm leading-6 text-muted-foreground">
              {guide.summary}
            </span>
          </Link>
        ))}
        {landingRoutes.map((route) => (
          <Link
            className="rounded-xl border p-4 transition-colors hover:bg-muted/50"
            href={route.href}
            key={route.href}
          >
            <span className="font-medium">{route.label}</span>
            <span className="mt-1 block text-sm leading-6 text-muted-foreground">
              Explore the supported backtesting workflow.
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
