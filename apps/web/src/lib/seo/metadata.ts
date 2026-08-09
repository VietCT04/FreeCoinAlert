import type { Metadata } from "next";

import { normalizeSeoRoutePath } from "./routes";
import { SEO_INDEXING_ENABLED, SITE_URL } from "./site";

export const ROOT_TITLE =
  "Free Crypto Strategy Backtesting & Alerts | FreeCoinAlert";
export const ROOT_DESCRIPTION =
  "Backtest supported crypto strategies on historical market data, inspect hypothetical trades and risk metrics, then monitor supported entry signals with Telegram alerts.";

const googleSiteVerification = process.env.GOOGLE_SITE_VERIFICATION?.trim();

const OPEN_GRAPH_IMAGE_PATH = "/opengraph-image";
const OPEN_GRAPH_IMAGE_ALT =
  "FreeCoinAlert crypto strategy backtesting and alert workflow";

type PublicMetadataOptions = {
  title: string;
  description: string;
  canonicalPath: string;
  openGraphDescription?: string;
  openGraphImage?: string;
  openGraphImageAlt?: string;
};

function getRobotsMetadata(): Metadata["robots"] {
  return {
    index: SEO_INDEXING_ENABLED,
    follow: SEO_INDEXING_ENABLED,
  };
}

function getAbsoluteUrl(path: string): string {
  return new URL(path, SITE_URL).toString();
}

export function createPublicMetadata({
  title,
  description,
  canonicalPath,
  openGraphDescription = description,
  openGraphImage = OPEN_GRAPH_IMAGE_PATH,
  openGraphImageAlt = OPEN_GRAPH_IMAGE_ALT,
}: PublicMetadataOptions): Metadata {
  const normalizedPath = normalizeSeoRoutePath(canonicalPath);
  const canonicalUrl = getAbsoluteUrl(normalizedPath);
  const imageUrl = getAbsoluteUrl(openGraphImage);

  return {
    title,
    description,
    alternates: {
      canonical: normalizedPath,
    },
    openGraph: {
      type: "website",
      url: canonicalUrl,
      siteName: "FreeCoinAlert",
      title,
      description: openGraphDescription,
      images: [
        {
          url: imageUrl,
          width: 1200,
          height: 630,
          alt: openGraphImageAlt,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description: openGraphDescription,
      images: [imageUrl],
    },
    robots: getRobotsMetadata(),
  };
}

export function createPrivateMetadata({
  title,
  description,
}: {
  title: string;
  description: string;
}): Metadata {
  return {
    title,
    description,
    robots: {
      index: false,
      follow: false,
    },
  };
}

export function createRootMetadata(): Metadata {
  return {
    metadataBase: new URL(SITE_URL),
    applicationName: "FreeCoinAlert",
    title: {
      default: ROOT_TITLE,
      template: "%s | FreeCoinAlert",
    },
    description: ROOT_DESCRIPTION,
    openGraph: {
      type: "website",
      siteName: "FreeCoinAlert",
      title: ROOT_TITLE,
      description: ROOT_DESCRIPTION,
      images: [
        {
          url: OPEN_GRAPH_IMAGE_PATH,
          width: 1200,
          height: 630,
          alt: OPEN_GRAPH_IMAGE_ALT,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: ROOT_TITLE,
      description: ROOT_DESCRIPTION,
      images: [OPEN_GRAPH_IMAGE_PATH],
    },
    ...(googleSiteVerification
      ? { verification: { google: googleSiteVerification } }
      : {}),
    robots: getRobotsMetadata(),
  };
}
