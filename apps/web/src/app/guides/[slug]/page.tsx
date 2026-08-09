import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { GuideLayout } from "../../../components/marketing/guides/guide-layout";
import { GUIDES, getGuideBySlug } from "../../../content/guides/registry";
import { createPublicMetadata } from "../../../lib/seo/metadata";

type GuidePageProps = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return GUIDES.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }: GuidePageProps): Promise<Metadata> {
  const { slug } = await params;
  const guide = getGuideBySlug(slug);

  if (!guide) {
    return {};
  }

  return createPublicMetadata({
    title: guide.metaTitle,
    description: guide.metaDescription,
    canonicalPath: `/guides/${guide.slug}`,
  });
}

export default async function GuidePage({ params }: GuidePageProps) {
  const { slug } = await params;
  const guide = getGuideBySlug(slug);

  if (!guide) {
    notFound();
  }

  const relatedGuides = guide.relatedGuideSlugs
    .map((relatedSlug) => getGuideBySlug(relatedSlug))
    .filter((relatedGuide): relatedGuide is NonNullable<typeof relatedGuide> => Boolean(relatedGuide));

  return <GuideLayout article={guide} relatedGuides={relatedGuides} />;
}
