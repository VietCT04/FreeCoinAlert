import Link from "next/link";

type BreadcrumbNavProps = {
  title: string;
};

export function BreadcrumbNav({ title }: BreadcrumbNavProps) {
  return (
    <nav aria-label="Breadcrumb" className="mb-8 text-sm text-muted-foreground">
      <ol className="flex flex-wrap items-center gap-2">
        <li>
          <Link className="transition-colors hover:text-foreground" href="/">
            Home
          </Link>
        </li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" className="font-medium text-foreground">
          {title}
        </li>
      </ol>
    </nav>
  );
}
