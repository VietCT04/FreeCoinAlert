import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const smaCrossoverBacktestingGuide: GuideArticle = {
  slug: "sma-crossover-backtesting",
  title: "SMA Crossover Backtesting for Crypto",
  metaTitle: "SMA Crossover Backtesting for Crypto",
  metaDescription:
    "Learn how FreeCoinAlert’s supported price/SMA 200 crossing is evaluated on confirmed candles and how to read its historical assumptions.",
  summary:
    "FreeCoinAlert currently supports a versioned price crossing of SMA 200. It does not provide an arbitrary fast-SMA/slow-SMA builder, so the backtest question must match the implemented preset.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "what-crossover-means", title: "What the supported crossing means" },
    { id: "supported-sma", title: "The SMA 200 calculation" },
    { id: "backtest-setup", title: "Set up a historical test" },
    { id: "read-results", title: "Read the report" },
    { id: "sma-limits", title: "Limits of the conclusion" },
  ],
  relatedGuideSlugs: ["how-to-backtest-crypto-strategy", "common-backtesting-mistakes"],
  relatedLandingRoutes: [
    { href: "/sma-backtest", label: "SMA backtest workflow" },
  ],
  body: (
    <>
      <section aria-labelledby="what-crossover-means" id="what-crossover-means">
        <h2 className="guide-heading">What the supported crossing means</h2>
        <p>
          A price/SMA crossing compares the confirmed candle close with the
          calculated simple moving average and looks for a direction change
          across the relationship. It is different from saying that price is
          merely above or below the average.
        </p>
        <p>
          FreeCoinAlert’s fixed preset catalog provides price crosses above or
          below SMA 200 on 1-hour and 4-hour candles. It does not claim that
          every SMA crossover variation is implemented.
        </p>
      </section>

      <section aria-labelledby="supported-sma" id="supported-sma">
        <h2 className="guide-heading">The SMA 200 calculation</h2>
        <p>
          The server calculation named <code>sma_close_v1</code> uses exactly
          200 confirmed close values. It requires those warm-up candles before
          a visible analysis range can emit a signal. The same versioned
          calculation is used by the live preset evaluator and the historical
          simulation boundary.
        </p>
        <GuideCallout title="Do not substitute an unsupported strategy">
          <p>
            A “20/50 SMA crossover” or an EMA crossover may be a valid research
            idea elsewhere, but it is not an implemented FreeCoinAlert preset
            unless the server catalog says so. Do not label a different test as
            this product’s SMA 200 result.
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="backtest-setup" id="backtest-setup">
        <h2 className="guide-heading">Set up a historical test</h2>
        <p>
          Choose one supported market and timeframe, a price/SMA 200 direction,
          a completed UTC date range, and explicit long-only exit assumptions if
          using the configurable path. The worker reads contiguous canonical
          candles and keeps the 200-candle warm-up outside the visible range.
        </p>
        <p>
          Entry is known at the confirmed signal-candle close, then the engine
          uses the next candle open under its disclosed slippage and fee rules.
          The report’s strategy and calculation snapshots preserve what was
          tested.
        </p>
      </section>

      <section aria-labelledby="read-results" id="read-results">
        <h2 className="guide-heading">Read the report</h2>
        <p>
          Inspect return, maximum drawdown, win rate, profit factor, trade
          count, and the individual hypothetical trades together. A crossover
          can occur rarely, and a long range with few trades may answer a
          narrower question than its duration suggests.
        </p>
        <p>
          Also review the data source, candle coverage, timeframe, range, and
          exit assumptions. Costs and the treatment of same-candle events can
          materially change a hypothetical outcome.
        </p>
      </section>

      <section aria-labelledby="sma-limits" id="sma-limits">
        <h2 className="guide-heading">Limits of the conclusion</h2>
        <p>
          A historical SMA crossing describes what the selected rule would have
          done on one stored sample under one engine version. It does not prove
          predictive power, profitability, or that a future crossing will have
          the same result.
        </p>
        <p>
          For a broader checklist, see <Link href="/guides/common-backtesting-mistakes">common crypto backtesting mistakes</Link>.
        </p>
      </section>
    </>
  ),
};
