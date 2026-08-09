import type { ReactNode } from "react";

export type GuideSection = {
  id: string;
  title: string;
};

export type GuideLink = {
  href: string;
  label: string;
};

export type GuideArticle = {
  slug: string;
  title: string;
  metaTitle: string;
  metaDescription: string;
  summary: string;
  publishedAt: string;
  updatedAt: string;
  author: "FreeCoinAlert";
  sections: readonly GuideSection[];
  relatedGuideSlugs: readonly string[];
  relatedLandingRoutes: readonly GuideLink[];
  historicalSimulation: boolean;
  body: ReactNode;
};
