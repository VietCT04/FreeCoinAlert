import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const cryptoTakeProfitStopLossGuide: GuideArticle = {
  slug: "crypto-take-profit-stop-loss",
  title: "Crypto Take-Profit and Stop-Loss Backtesting",
  metaTitle: "Crypto Take-Profit and Stop-Loss Backtesting",
  metaDescription:
    "Understand how take-profit and stop-loss levels are tested against OHLC candles, including gaps, same-candle ambiguity, costs, and slippage.",
  summary:
    "Take-profit and stop-loss rules turn an entry into an exit plan. On OHLC candles, the engine can test levels and disclose priorities, but it cannot know the exact intrabar path.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "relative-levels", title: "Levels relative to entry" },
    { id: "ohlc-testing", title: "How OHLC candles test levels" },
    { id: "gap-and-same-candle", title: "Gaps and same-candle ambiguity" },
    { id: "costs-and-slippage", title: "Fees and slippage" },
    { id: "read-limits", title: "Read the result with its limits" },
  ],
  relatedGuideSlugs: ["backtesting-fees-slippage", "how-to-backtest-crypto-strategy"],
  relatedLandingRoutes: [
    { href: "/tp-sl-backtest", label: "TP/SL backtest workflow" },
  ],
  body: (
    <>
      <section aria-labelledby="relative-levels" id="relative-levels">
        <h2 className="guide-heading">Levels relative to entry</h2>
        <p>
          A take-profit (TP) level is a target above the long entry price. A
          stop-loss (SL) level is a protective threshold below it. In a
          historical strategy, the percentages are stored as part of the
          immutable strategy snapshot, so the report can be understood without
          guessing which rules were used.
        </p>
        <p>
          For example, a long plan might use TP +6%, SL -3%, and a maximum
          holding period of 7 candles. That is an input example only; it does
          not represent a reported market outcome.
        </p>
      </section>

      <section aria-labelledby="ohlc-testing" id="ohlc-testing">
        <h2 className="guide-heading">How OHLC candles test levels</h2>
        <p>
          The configurable engine uses exact Decimal arithmetic to derive the
          levels from the raw entry price. A candle high touching the TP level
          can trigger a take-profit exit. A candle low touching the SL level can
          trigger a stop-loss exit. The report preserves the exit reason and
          price basis supplied by the server.
        </p>
        <p>
          The engine first checks whether the candle opens beyond a stop level;
          that is recorded as a gap-through-stop at the opening price. Otherwise
          a low touching the level uses the stop-loss level as its price basis.
        </p>
      </section>

      <section aria-labelledby="gap-and-same-candle" id="gap-and-same-candle">
        <h2 className="guide-heading">Gaps and same-candle ambiguity</h2>
        <p>
          If a candle opens below a long stop level, the historical engine uses
          the open rather than pretending the level was fillable. This models a
          gap-through-stop assumption, not a guaranteed real-world fill.
        </p>
        <p>
          OHLC data may show that both a low reached the stop and a high reached
          the target during one candle, but it does not show which happened
          first. FreeCoinAlert uses a documented conservative priority: stop
          loss before take profit, then RSI threshold exit, then maximum
          holding. That deterministic choice makes the report reproducible, not
          omniscient.
        </p>
        <GuideCallout title="Intrabar order is unknown" tone="caution">
          <p>
            Do not present an OHLC backtest as a tick-by-tick reconstruction.
            The exact path inside a candle is unavailable unless a more detailed
            data source and a different approved engine are used.
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="costs-and-slippage" id="costs-and-slippage">
        <h2 className="guide-heading">Fees and slippage</h2>
        <p>
          Gross price movement is not the same as net simulated performance.
          Entry and exit slippage make the fills less favorable, while fees are
          charged on both sides under the selected engine assumptions. The
          server applies those assumptions with exact Decimal arithmetic and
          exposes them with the report.
        </p>
        <p>
          Read <Link href="/guides/backtesting-fees-slippage">backtesting fees and slippage</Link> for why a small-looking cost can matter when a strategy trades frequently or has narrow targets.
        </p>
      </section>

      <section aria-labelledby="read-limits" id="read-limits">
        <h2 className="guide-heading">Read the result with its limits</h2>
        <p>
          Check the date range, timeframe, trade count, drawdown, exit-reason
          breakdown, data coverage, and strategy fingerprint together. A TP/SL
          rule can change the distribution of wins and losses without proving
          that its levels will work in a future market.
        </p>
        <p>
          Historical exits are hypothetical. They do not place an order, track a
          live position, or guarantee that a real venue would fill at the same
          price.
        </p>
      </section>
    </>
  ),
};
