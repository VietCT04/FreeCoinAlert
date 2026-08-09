import { SeoLandingShell } from "@/components/marketing/seo/seo-landing-shell";
import { getSeoLandingMetadata, getSeoLandingPage } from "@/content/seo/landing-pages";

export const metadata = getSeoLandingMetadata("/crypto-strategy-tester");

export default function CryptoStrategyTesterPage() {
  return <SeoLandingShell page={getSeoLandingPage("/crypto-strategy-tester")} />;
}
