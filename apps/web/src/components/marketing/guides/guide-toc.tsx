import Link from "next/link";

import type { GuideSection } from "../../../content/guides/types";

export function GuideToc({ sections }: { sections: readonly GuideSection[] }) {
  if (sections.length < 3) {
    return null;
  }

  return (
    <nav
      aria-label="On this page"
      className="rounded-xl border bg-muted/30 p-5"
    >
      <p className="text-sm font-semibold">On this page</p>
      <ol className="mt-3 grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
        {sections.map((section, index) => (
          <li key={section.id}>
            <Link
              className="hover:text-foreground"
              href={`#${section.id}`}
            >
              <span className="mr-2 text-xs text-muted-foreground/70">
                {index + 1}.
              </span>
              {section.title}
            </Link>
          </li>
        ))}
      </ol>
    </nav>
  );
}
