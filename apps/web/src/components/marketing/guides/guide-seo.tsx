import { SITE_URL } from "../../../lib/seo/site";
import { JsonLd } from "../../../lib/seo/structured-data";

type JsonLdValue = Record<string, unknown>;

export function guideCanonicalUrl(path: string): string {
  return new URL(path, SITE_URL).toString();
}

export function GuideJsonLd({ value }: { value: JsonLdValue }) {
  return <JsonLd data={value} />;
}

export function createBreadcrumbJsonLd(items: readonly { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: guideCanonicalUrl(item.path),
    })),
  };
}
