import { AuthAwareBacktestCta } from "@/components/marketing/auth-aware-backtest-cta";

export function FinalCta() {
  return (
    <section className="scroll-mt-24 py-20 sm:py-24" id="start">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6 rounded-3xl bg-primary px-6 py-10 text-primary-foreground sm:px-10 sm:py-12 md:flex-row md:items-center md:justify-between">
          <h2 className="max-w-xl font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
            Test the strategy before you watch for it.
          </h2>
          <div className="[&_a]:shadow-sm">
            <AuthAwareBacktestCta showSecondary={false} />
          </div>
        </div>
      </div>
    </section>
  );
}
