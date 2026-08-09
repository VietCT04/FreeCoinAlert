import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const rsiBacktestingGuide: GuideArticle = {
  slug: "rsi-backtesting",
  title: "RSI Backtesting for Crypto Strategies",
  metaTitle: "RSI Backtesting for Crypto Strategies",
  metaDescription:
    "Learn how RSI threshold crossings are evaluated on confirmed crypto candles and why exits, costs, timeframe, and range shape a historical result.",
  summary:
    "RSI is a momentum oscillator, not a reversal guarantee. This guide explains FreeCoinAlert’s implemented Wilder RSI(14) close input, threshold-cross semantics, and the assumptions that make a backtest reproducible.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "what-rsi-measures", title: "What RSI measures" },
    { id: "implemented-rsi", title: "The implemented RSI calculation" },
    { id: "threshold-cross", title: "Threshold crossings" },
    { id: "entry-or-exit", title: "Entry versus indicator exit" },
    { id: "read-results", title: "How to read a result" },
    { id: "rsi-limits", title: "Limits and interpretation" },
  ],
  relatedGuideSlugs: ["rsi-cross-below-30-strategy", "how-to-backtest-crypto-strategy"],
  relatedLandingRoutes: [
    { href: "/rsi-backtest", label: "RSI backtest workflow" },
  ],
  body: (
    <>
      <section aria-labelledby="what-rsi-measures" id="what-rsi-measures">
        <h2 className="guide-heading">What RSI measures</h2>
        <p>
          The Relative Strength Index (RSI) summarizes recent upward and
          downward close-to-close movement on a bounded 0–100 scale. It is
          commonly used to describe momentum conditions, but an “overbought”
          or “oversold” reading does not guarantee that price will reverse.
        </p>
        <p>
          A historical RSI result depends on the entry, exit plan, timeframe,
          costs, slippage, and selected range. RSI is one input to an experiment,
          not the experiment’s conclusion.
        </p>
      </section>

      <section aria-labelledby="implemented-rsi" id="implemented-rsi">
        <h2 className="guide-heading">The implemented RSI calculation</h2>
        <p>
          FreeCoinAlert’s supported RSI uses Wilder RSI 14 with confirmed
          candle-close input. The server uses 15 complete closes to establish
          the initial 14 changes, then applies Wilder’s smoothing to subsequent
          values. The calculation is pinned as <code>rsi_wilder_close_v1</code>.
        </p>
        <p>
          Historical analysis currently evaluates the supported 1-hour and
          4-hour preset timeframes from canonical stored candles. The browser
          displays server results; it does not recompute RSI from a chart.
        </p>
        <GuideCallout title="Versioned meaning matters">
          <p>
            A published preset version keeps its calculation meaning. A future
            calculation change requires a new version rather than silently
            changing old signal or report semantics.
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="threshold-cross" id="threshold-cross">
        <h2 className="guide-heading">Threshold crossings</h2>
        <p>
          A threshold condition asks whether RSI is on one side of a level. A
          threshold crossing asks whether the prior value was on the other side
          and the current confirmed value has crossed or reached the boundary
          according to the platform’s equality-aware rule.
        </p>
        <p>
          That distinction matters: “RSI below 30” may remain true for many
          candles, while “RSI crosses below 30” describes a transition. See the
          focused <Link href="/guides/rsi-cross-below-30-strategy">RSI crosses below 30 guide</Link> for a concrete setup.
        </p>
      </section>

      <section aria-labelledby="entry-or-exit" id="entry-or-exit">
        <h2 className="guide-heading">Entry versus indicator exit</h2>
        <p>
          RSI can be the selected entry preset, or a supported RSI threshold
          cross can be one of the configurable historical exit rules. Those are
          different roles. An RSI entry starts the hypothetical position under
          the configured execution assumptions; an RSI exit closes a long
          position when its exit condition is met.
        </p>
        <p>
          The server keeps direction, timeframe, threshold, and calculation
          version in the immutable strategy snapshot so a report can be read in
          context later.
        </p>
      </section>

      <section aria-labelledby="read-results" id="read-results">
        <h2 className="guide-heading">How to read an RSI backtest</h2>
        <p>
          Review the complete context before looking at a headline metric:
          market, timeframe, UTC range, entry preset, exit rules, data
          coverage, trade count, fees, slippage, and maximum drawdown. A high
          win rate can coexist with a poor return when losing trades are larger
          or costs are significant.
        </p>
        <ul>
          <li>Check whether the range contains enough trades to make the result meaningful to your question.</li>
          <li>Check that entries use only confirmed candle information and the next-candle execution assumption.</li>
          <li>Compare the risk path, not only the final equity value.</li>
          <li>Record the exact strategy and calculation versions before comparing reports.</li>
        </ul>
      </section>

      <section aria-labelledby="rsi-limits" id="rsi-limits">
        <h2 className="guide-heading">Limits and interpretation</h2>
        <p>
          RSI does not predict prices, identify a guaranteed bottom, or turn a
          historical simulation into financial advice. Momentum can remain
          extreme, and a signal can be followed by a loss under the selected
          exit and cost assumptions.
        </p>
        <p>
          Use RSI backtesting to make a defined historical question inspectable.
          It is not a reason to remove position sizing, risk limits, or human
          judgment from future decisions.
        </p>
      </section>
    </>
  ),
};
