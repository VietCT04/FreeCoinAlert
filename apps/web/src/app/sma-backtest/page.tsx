import { SeoLandingShell } from "@/components/marketing/seo/seo-landing-shell";
import { getSeoLandingMetadata, getSeoLandingPage } from "@/content/seo/landing-pages";

export const metadata = getSeoLandingMetadata("/sma-backtest");

export default function SmaBacktestPage() {
  return <SeoLandingShell page={getSeoLandingPage("/sma-backtest")} />;
}
