import Link from "next/link";

type RelatedPage = {
  href: string;
  label: string;
};

type RelatedPagesProps = {
  pages: readonly RelatedPage[];
};

export function RelatedPages({ pages }: RelatedPagesProps) {
  if (pages.length === 0) {
    return null;
  }

  return (
    <section aria-labelledby="related-pages-heading" className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight" id="related-pages-heading">
        Continue exploring
      </h2>
      <ul className="grid gap-3 sm:grid-cols-2">
        {pages.map((page) => (
          <li key={page.href}>
            <Link
              className="block rounded-xl border bg-card p-4 font-medium text-foreground transition-colors hover:border-primary hover:bg-accent"
              href={page.href}
            >
              {page.label}
              <span aria-hidden="true" className="ml-2 text-muted-foreground">
                →
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
