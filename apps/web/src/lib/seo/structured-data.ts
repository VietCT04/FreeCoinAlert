import { createElement, type ReactNode } from "react";

import { ROOT_DESCRIPTION } from "./metadata";
import { SITE_URL } from "./site";

export function serializeJsonLd(value: unknown): string {
  const serializedValue = JSON.stringify(value);

  if (serializedValue === undefined) {
    throw new Error("Structured data must be JSON serializable.");
  }

  return serializedValue.replace(/</g, "\\u003c");
}

export function createWebSiteStructuredData({
  description = ROOT_DESCRIPTION,
  url = new URL("/", SITE_URL).toString(),
}: {
  description?: string;
  url?: string;
} = {}) {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "FreeCoinAlert",
    url,
    description,
  };
}

export function JsonLd({ data }: { data: unknown }): ReactNode {
  return createElement("script", {
    dangerouslySetInnerHTML: { __html: serializeJsonLd(data) },
    type: "application/ld+json",
  });
}
