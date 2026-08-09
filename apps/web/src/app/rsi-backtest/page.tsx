import { SeoLandingShell } from "@/components/marketing/seo/seo-landing-shell";
import { getSeoLandingMetadata, getSeoLandingPage } from "@/content/seo/landing-pages";

export const metadata = getSeoLandingMetadata("/rsi-backtest");

export default function RsiBacktestPage() {
  return <SeoLandingShell page={getSeoLandingPage("/rsi-backtest")} />;
}
