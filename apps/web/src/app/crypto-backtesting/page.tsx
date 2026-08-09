import { SeoLandingShell } from "@/components/marketing/seo/seo-landing-shell";
import { getSeoLandingMetadata, getSeoLandingPage } from "@/content/seo/landing-pages";

export const metadata = getSeoLandingMetadata("/crypto-backtesting");

export default function CryptoBacktestingPage() {
  return <SeoLandingShell page={getSeoLandingPage("/crypto-backtesting")} />;
}
