import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BellRing,
  Check,
  CircleHelp,
  ShieldCheck,
} from "lucide-react";

import { AuthAwareBacktestCta } from "../components/marketing/auth-aware-backtest-cta";
import { MarketingFooter } from "../components/marketing/marketing-footer";
import { MarketingHeader } from "../components/marketing/marketing-header";
import { MarketingSection } from "../components/marketing/marketing-section";
import { StrategyExampleCard } from "../components/marketing/strategy-example-card";
import { Button } from "../components/ui/button";
import { createPublicMetadata } from "../lib/seo/metadata";
import { createWebSiteStructuredData, JsonLd } from "../lib/seo/structured-data";

export const metadata = createPublicMetadata({
  title: "Free Crypto Backtesting & Strategy Alerts",
  description:
    "Backtest RSI, SMA, take-profit, stop-loss and time-based crypto strategies on historical Binance Spot data, inspect hypothetical results, then monitor supported entry signals with Telegram alerts.",
  canonicalPath: "/",
});

const testedConcepts = [
  "RSI(14) threshold-cross entry signals",
  "Price / SMA(200) crossover entry signals",
  "Take-profit and stop-loss percentages",
  "RSI indicator exits where supported",
  "Maximum-holding-candle exits",
  "1h and 4h preset timeframes",
];

const assumptions = [
  "Signals are confirmed at candle close.",
  "Entry occurs at the next candle open.",
  "Fees and adverse slippage are modeled.",
  "Only one hypothetical position is open at a time.",
  "Overlapping entry signals are ignored while a position is open.",
  "Same-candle exit ambiguity follows the documented conservative priority.",
  "Results are historical hypothetical simulations, not predictions.",
];

const reportOutputs = [
  "Net return and maximum drawdown",
  "Win rate and profit factor",
  "Hypothetical trades and exit reasons",
  "Price chart with entry and exit markers",
  "Equity progression",
  "Methodology and version fingerprints",
];

const faqs = [
  {
    question: "Is a backtest a prediction?",
    answer:
      "No. A backtest is a historical, hypothetical simulation using stored candles and stated assumptions. It does not predict future prices or outcomes.",
  },
  {
    question: "Does FreeCoinAlert place trades?",
    answer:
      "No. FreeCoinAlert does not connect to exchange trading accounts or execute orders. It can monitor supported entry signals and deliver alerts through Telegram.",
  },
  {
    question: "Can I test take profit and stop loss?",
    answer:
      "Yes, supported configurable strategies can include take-profit, stop-loss, indicator, and maximum-holding exits. The report explains the execution assumptions used.",
  },
  {
    question: "What happens if take profit and stop loss occur in the same candle?",
    answer:
      "The server uses a documented conservative priority so the result remains deterministic rather than choosing the more favorable outcome.",
  },
  {
    question: "What does monitoring an entry monitor?",
    answer:
      "Live monitoring watches the supported entry preset only. It does not turn historical take-profit, stop-loss, or holding-period rules into live positions or trade execution.",
  },
];

export default function Home() {
  return (
    <div className="min-h-svh bg-background text-foreground">
      <MarketingHeader showHomeSections />
      <main>
        <JsonLd
          data={createWebSiteStructuredData({
            description:
              "Backtest supported crypto strategies and monitor supported entry signals.",
          })}
        />

        <section className="border-b bg-muted/20" id="top">
          <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)] lg:items-center lg:px-8 lg:py-28">
            <div className="max-w-3xl space-y-7">
              <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                Historical strategy testing
              </p>
              <h1 className="font-heading text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
                Backtest Crypto Strategies for Free
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl">
                Define a supported entry and exit plan. Test it against
                historical crypto candles. Monitor the same entry signal after
                the backtest.
              </p>
              <AuthAwareBacktestCta />
              <Link
                className="inline-flex items-center gap-2 text-sm font-medium text-foreground underline-offset-4 hover:underline"
                href="#how-it-works"
              >
                See how it works
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
              <p className="text-sm leading-6 text-muted-foreground">
                Historical results are hypothetical. FreeCoinAlert does not
                execute trades or promise delivery or profit.
              </p>
            </div>

            <div className="rounded-2xl border bg-card p-5 shadow-sm sm:p-6">
              <div className="flex items-center justify-between gap-4 border-b pb-4">
                <div>
                  <p className="text-sm font-medium">Your workflow</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    From an idea to a monitored entry
                  </p>
                </div>
                <BarChart3 aria-hidden="true" className="size-8 text-primary" />
              </div>
              <ol className="mt-5 space-y-4">
                {["Build a supported strategy", "Backtest historical candles", "Understand the report", "Monitor the entry"].map(
                  (step, index) => (
                    <li className="flex items-center gap-3" key={step}>
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                        {index + 1}
                      </span>
                      <span className="text-sm font-medium">{step}</span>
                    </li>
                  ),
                )}
              </ol>
            </div>
          </div>
        </section>

        <div className="mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8">
          <MarketingSection
            description="Use one guided flow to define a supported strategy, run it against complete stored candles, and decide whether the entry condition is worth monitoring."
            eyebrow="The workflow"
            id="how-it-works"
            title="How it works"
          >
            <ol className="grid gap-4 md:grid-cols-4">
              {[
                ["Build strategy", "Choose a supported entry, direction, timeframe, and exit plan."],
                ["Backtest", "Run a bounded historical simulation using canonical stored candles."],
                ["Understand results", "Review metrics, hypothetical trades, markers, equity, and assumptions."],
                ["Monitor the entry", "Receive an alert when the supported entry condition occurs again."],
              ].map(([title, description], index) => (
                <li className="rounded-xl border bg-card p-5" key={title}>
                  <span className="text-sm font-semibold text-primary">0{index + 1}</span>
                  <h3 className="mt-4 font-heading text-lg font-semibold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
                </li>
              ))}
            </ol>
            <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
              The last step alerts on the supported entry condition only. It
              does not turn historical take-profit, stop-loss, or holding rules
              into live trade execution.
            </p>
          </MarketingSection>

          <MarketingSection
            description="See the kind of configuration the current backtester can represent without relying on invented performance numbers."
            eyebrow="A concrete example"
            id="example-strategy"
            title="Example strategy"
          >
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.8fr)] lg:items-start">
              <StrategyExampleCard />
              <div className="space-y-4 rounded-xl border bg-muted/30 p-5">
                <div className="flex items-center gap-3">
                  <ShieldCheck aria-hidden="true" className="size-5 text-primary" />
                  <h3 className="font-heading font-semibold">Why the detail matters</h3>
                </div>
                <p className="text-sm leading-6 text-muted-foreground">
                  Entry timing, costs, holding periods, and same-candle rules
                  can change a hypothetical result. The report keeps these
                  assumptions visible so the numbers can be interpreted in
                  context.
                </p>
              </div>
            </div>
          </MarketingSection>

          <MarketingSection
            description="The product supports a constrained set of versioned concepts. It does not accept arbitrary strategy code or promise an optimized result."
            eyebrow="Supported inputs"
            id="what-you-can-test"
            title="What you can test"
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {testedConcepts.map((concept) => (
                <div className="flex items-start gap-3 rounded-xl border bg-card p-4" key={concept}>
                  <Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
                  <p className="text-sm leading-6">{concept}</p>
                </div>
              ))}
            </div>
          </MarketingSection>

          <MarketingSection
            description="These server-owned rules make the simulation reproducible and help you read a result without confusing it with a live trade."
            eyebrow="Read the fine print"
            id="assumptions"
            title="Backtesting assumptions that matter"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              {assumptions.map((assumption) => (
                <div className="flex items-start gap-3 rounded-xl border bg-card p-4" key={assumption}>
                  <CircleHelp aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <p className="text-sm leading-6">{assumption}</p>
                </div>
              ))}
            </div>
          </MarketingSection>

          <MarketingSection
            description="The existing report gives you context for the simulation instead of reducing it to one headline number."
            eyebrow="Inspect the result"
            id="understand-results"
            title="Understand the result"
          >
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {reportOutputs.map((output) => (
                <div className="rounded-xl border bg-card p-5" key={output}>
                  <p className="text-sm font-medium">{output}</p>
                </div>
              ))}
            </div>
          </MarketingSection>

          <MarketingSection
            description="A historical simulation can include exits that are useful for analysis. Live monitoring stays narrower and watches the supported entry preset only."
            eyebrow="After the report"
            id="entry-alerts"
            title="From backtest to live entry alert"
          >
            <div className="grid gap-5 md:grid-cols-2">
              <div className="rounded-xl border bg-card p-6">
                <p className="text-sm font-semibold text-primary">Backtest</p>
                <p className="mt-3 font-heading text-xl font-semibold">Entry + TP + SL + indicator/time exits</p>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Review how the complete supported plan would have behaved in
                  the selected historical range.
                </p>
              </div>
              <div className="rounded-xl border bg-card p-6">
                <p className="text-sm font-semibold text-primary">Live monitoring</p>
                <p className="mt-3 font-heading text-xl font-semibold">The supported entry preset only</p>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Connect Telegram when you are ready to receive a notification
                  for a future supported entry occurrence. No orders are placed.
                </p>
              </div>
            </div>
            <AuthAwareBacktestCta />
          </MarketingSection>

          <MarketingSection
            description="Historical analysis uses the controlled Binance Spot USDT market catalogue available to the product. Coverage and data assumptions are shown in each report."
            eyebrow="Data boundary"
            id="supported-markets"
            title="Supported market context"
          >
            <div className="rounded-xl border bg-muted/30 p-6">
              <div className="flex items-start gap-3">
                <BellRing aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-primary" />
                <div className="space-y-2">
                  <h3 className="font-heading text-lg font-semibold">Controlled Binance Spot coverage</h3>
                  <p className="text-sm leading-6 text-muted-foreground">
                    This is not exchange-wide or all-coin support. The server
                    decides which markets and timeframes are available, and the
                    browser uses those returned choices.
                  </p>
                </div>
              </div>
            </div>
          </MarketingSection>

          <MarketingSection
            description="Short answers to the questions that matter before you start a historical simulation."
            eyebrow="Questions"
            id="faq"
            title="Frequently asked questions"
          >
            <div className="divide-y rounded-xl border bg-card px-5">
              {faqs.map(({ answer, question }) => (
                <details className="group py-5" key={question}>
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium outline-none marker:hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-4">
                    {question}
                    <ArrowRight aria-hidden="true" className="size-4 shrink-0 transition-transform group-open:rotate-90" />
                  </summary>
                  <p className="mt-3 max-w-3xl pr-8 text-sm leading-6 text-muted-foreground">{answer}</p>
                </details>
              ))}
            </div>
          </MarketingSection>

          <section className="border-t py-16 sm:py-20" id="start">
            <div className="rounded-2xl bg-primary px-6 py-10 text-primary-foreground sm:px-10">
              <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                <div className="max-w-2xl space-y-3">
                  <h2 className="font-heading text-3xl font-semibold tracking-tight">Build a strategy → backtest it → monitor the entry.</h2>
                  <p className="text-sm leading-6 text-primary-foreground/80">
                    Start with a supported historical configuration and keep
                    the assumptions visible at every step.
                  </p>
                </div>
                <Button asChild size="lg" variant="secondary">
                  <Link href="/sign-up">
                    Start backtesting
                    <ArrowRight aria-hidden="true" />
                  </Link>
                </Button>
              </div>
            </div>
          </section>
        </div>
      </main>
      <MarketingFooter />
    </div>
  );
}
