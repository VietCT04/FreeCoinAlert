import { Hero } from "@/components/marketing/homepage/hero";
import { Differentiation } from "@/components/marketing/homepage/differentiation";
import { FinalCta } from "@/components/marketing/homepage/final-cta";
import { HomepageFaq } from "@/components/marketing/homepage/homepage-faq";
import { MethodologyDisclosure } from "@/components/marketing/homepage/methodology-disclosure";
import { ProductFlow } from "@/components/marketing/homepage/product-flow";
import { ProductProofStrip } from "@/components/marketing/homepage/product-proof-strip";
import { ProductShowcase } from "@/components/marketing/homepage/product-showcase";
import { MarketingFooter } from "@/components/marketing/marketing-footer";
import { MarketingHeader } from "@/components/marketing/marketing-header";
import { createPublicMetadata } from "@/lib/seo/metadata";
import { createWebSiteStructuredData, JsonLd } from "@/lib/seo/structured-data";

export const metadata = createPublicMetadata({
  title: "Crypto Strategy Backtesting & Alerts | FreeCoinAlert",
  description:
    "Backtest supported crypto entry and exit strategies on historical Binance Spot data, inspect hypothetical results and execution assumptions, then monitor supported entry signals with Telegram alerts.",
  canonicalPath: "/",
  openGraphImageAlt:
    "FreeCoinAlert crypto strategy backtesting product preview with an XRPUSDT RSI strategy",
});

export default function Home() {
  return (
    <div className="min-h-svh bg-background text-foreground">
      <MarketingHeader />
      <main>
        <JsonLd
          data={createWebSiteStructuredData({
            description:
              "Backtest supported crypto strategies and monitor supported entry signals.",
          })}
        />

        <Hero />

        <div className="mx-auto w-full max-w-6xl px-4 pt-6 sm:px-6 sm:pt-8 lg:px-8">
          <ProductProofStrip />
        </div>

        <ProductFlow />
        <ProductShowcase />
        <Differentiation />
        <MethodologyDisclosure />
        <HomepageFaq />
        <FinalCta />
      </main>
      <MarketingFooter />
    </div>
  );
}
