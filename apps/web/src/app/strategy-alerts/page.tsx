import { SeoLandingShell } from "@/components/marketing/seo/seo-landing-shell";
import { getSeoLandingMetadata, getSeoLandingPage } from "@/content/seo/landing-pages";

export const metadata = getSeoLandingMetadata("/strategy-alerts");

export default function StrategyAlertsPage() {
  return <SeoLandingShell page={getSeoLandingPage("/strategy-alerts")} />;
}
