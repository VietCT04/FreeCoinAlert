import { SeoLandingShell } from "@/components/marketing/seo/seo-landing-shell";
import { getSeoLandingMetadata, getSeoLandingPage } from "@/content/seo/landing-pages";

export const metadata = getSeoLandingMetadata("/tp-sl-backtest");

export default function TpSlBacktestPage() {
  return <SeoLandingShell page={getSeoLandingPage("/tp-sl-backtest")} />;
}
