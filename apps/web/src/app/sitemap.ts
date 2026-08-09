import type { MetadataRoute } from "next";

import { PUBLIC_SEO_ROUTES, normalizeSeoRoutePath } from "../lib/seo/routes";
import { SEO_INDEXING_ENABLED, SITE_URL } from "../lib/seo/site";

export default function sitemap(): MetadataRoute.Sitemap {
  if (!SEO_INDEXING_ENABLED) {
    return [];
  }

  return PUBLIC_SEO_ROUTES.map(({ path }) => ({
    url: new URL(normalizeSeoRoutePath(path), SITE_URL).toString(),
  }));
}
