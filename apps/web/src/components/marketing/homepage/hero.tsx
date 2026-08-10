import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { AuthAwareBacktestCta } from "@/components/marketing/auth-aware-backtest-cta";

import { HeroProductDemo } from "./hero-product-demo";

export function Hero() {
  return (
    <section
      aria-labelledby="homepage-hero-heading"
      className="marketing-homepage__hero relative isolate overflow-hidden border-b"
      id="product-showcase"
    >
      <div aria-hidden="true" className="marketing-homepage__hero-depth" />
      <div className="relative mx-auto grid w-full max-w-6xl gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)] lg:items-center lg:px-8 lg:py-28">
        <div className="max-w-3xl space-y-7">
          <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            Crypto strategy backtesting
          </p>
          <h1
            className="max-w-2xl font-heading text-4xl font-semibold tracking-tight text-balance sm:text-6xl"
            id="homepage-hero-heading"
          >
            Backtest a crypto strategy before you trust it.
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl">
            Define the rules. Test them on historical crypto data. Understand
            the result, then get alerted when the entry appears again.
          </p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-4">
            <AuthAwareBacktestCta showSecondary={false} />
            <Link
              className="inline-flex items-center gap-2 text-sm font-medium text-foreground underline-offset-4 hover:underline"
              href="#product-showcase"
            >
              View example
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </div>
          <p className="flex max-w-xl items-start gap-2 text-sm leading-6 text-muted-foreground">
            <ShieldCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            Historical simulations only · No exchange trading keys · No order
            execution
          </p>
        </div>

        <HeroProductDemo />
      </div>
    </section>
  );
}
