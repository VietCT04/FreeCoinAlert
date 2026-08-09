import { SeoLandingShell } from "@/components/marketing/seo/seo-landing-shell";
import { getSeoLandingMetadata, getSeoLandingPage } from "@/content/seo/landing-pages";

export const metadata = getSeoLandingMetadata("/bitcoin-backtest");

export default function BitcoinBacktestPage() {
  return <SeoLandingShell page={getSeoLandingPage("/bitcoin-backtest")} />;
}
