import { AuthAwareBacktestCta } from "@/components/marketing/auth-aware-backtest-cta";

type BacktestCtaProps = {
  heading: string;
  body: string;
};

export function BacktestCta({ heading, body }: BacktestCtaProps) {
  return (
    <section
      aria-labelledby="backtest-cta-heading"
      className="rounded-2xl bg-primary p-6 text-primary-foreground shadow-sm sm:p-8"
    >
      <h2 className="text-2xl font-semibold tracking-tight" id="backtest-cta-heading">
        {heading}
      </h2>
      <p className="mt-3 max-w-2xl leading-7 text-primary-foreground/80">{body}</p>
      <div className="mt-6">
        <AuthAwareBacktestCta />
      </div>
    </section>
  );
}
