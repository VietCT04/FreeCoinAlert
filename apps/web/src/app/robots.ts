import type { MetadataRoute } from "next";

import { SEO_INDEXING_ENABLED, SITE_URL } from "../lib/seo/site";

export default function robots(): MetadataRoute.Robots {
  if (!SEO_INDEXING_ENABLED) {
    return {
      rules: {
        userAgent: "*",
        allow: "/_next/",
        disallow: "/",
      },
    };
  }

  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: new URL(SITE_URL).host,
  };
}
