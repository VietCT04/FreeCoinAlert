import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const commonBacktestingMistakesGuide: GuideArticle = {
  slug: "common-backtesting-mistakes",
  title: "Common Crypto Backtesting Mistakes",
  metaTitle: "Common Crypto Backtesting Mistakes",
  metaDescription:
    "Avoid look-ahead bias, unclear exits, ignored costs, overfitting, and confusing historical alerts with trade execution when testing crypto strategies.",
  summary:
    "The most useful backtest is explicit about timing, costs, exits, drawdown, data coverage, and what the product does not do. These mistakes make a historical result look more certain than it is.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "look-ahead", title: "Using future information" },
    { id: "ignore-costs", title: "Ignoring fees and slippage" },
    { id: "unclear-exits", title: "Leaving exits unclear" },
    { id: "overfit", title: "Overfitting the sample" },
    { id: "ignore-drawdown", title: "Ignoring drawdown" },
    { id: "ohlc-path", title: "Assuming OHLC reveals intrabar order" },
    { id: "alert-execution", title: "Confusing alerts with execution" },
  ],
  relatedGuideSlugs: ["how-to-backtest-crypto-strategy", "backtesting-vs-forward-testing"],
  relatedLandingRoutes: [
    { href: "/crypto-backtesting", label: "Crypto backtesting workflow" },
  ],
  body: (
    <>
      <section aria-labelledby="look-ahead" id="look-ahead">
        <h2 className="guide-heading">Using future information</h2>
        <p>
          Look-ahead bias happens when a decision uses a price, indicator, or
          outcome that was not known at the decision time. A candle-close signal
          must not use the next candle’s high, low, or close to decide its entry.
        </p>
        <p>
          FreeCoinAlert’s historical boundary knows a confirmed signal at the
          signal-candle close and schedules entry at the next candle open. The
          worker calculates from an immutable dataset snapshot.
        </p>
      </section>

      <section aria-labelledby="ignore-costs" id="ignore-costs">
        <h2 className="guide-heading">Ignoring fees and slippage</h2>
        <p>
          A price-only result can look stronger than a net result after entry and
          exit costs. Review the engine’s fee and slippage assumptions and keep
          them consistent when comparing reports.
        </p>
        <p>
          See <Link href="/guides/backtesting-fees-slippage">backtesting fees and slippage</Link> for the product’s modeled cost boundary.
        </p>
      </section>

      <section aria-labelledby="unclear-exits" id="unclear-exits">
        <h2 className="guide-heading">Leaving exits unclear</h2>
        <p>
          “Buy when RSI is low” is not a complete historical strategy. State
          whether the exit is TP, SL, an indicator crossing, a holding limit, or
          another supported rule. FreeCoinAlert validates a bounded configurable
          exit plan and records it with the report.
        </p>
        <p>
          A report with a different exit plan answers a different question even
          when its entry condition is identical.
        </p>
      </section>

      <section aria-labelledby="overfit" id="overfit">
        <h2 className="guide-heading">Overfitting the sample</h2>
        <p>
          Testing many parameter combinations or repeatedly moving the date
          range until one result looks attractive can fit noise in the selected
          history. Keep a record of the question, rules, and range, then use a
          separate future period for observation.
        </p>
        <GuideCallout title="One result is one scenario" tone="caution">
          <p>
            A historical report is not a ranking of strategies and does not
            establish that a rule is “best” or “winning.”
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="ignore-drawdown" id="ignore-drawdown">
        <h2 className="guide-heading">Ignoring drawdown</h2>
        <p>
          Final return does not describe the path taken to reach it. Maximum
          drawdown, trade count, losing streaks, and exit-reason counts provide
          important context for a hypothetical equity curve.
        </p>
        <p>
          A high win rate can still accompany a poor risk profile if losses are
          larger than wins or costs consume the edge.
        </p>
      </section>

      <section aria-labelledby="ohlc-path" id="ohlc-path">
        <h2 className="guide-heading">Assuming OHLC reveals intrabar order</h2>
        <p>
          High and low values show that levels were reached, not which was
          reached first. Same-candle TP/SL ambiguity requires a documented
          priority. FreeCoinAlert applies a deterministic conservative rule and
          exposes the price basis; it does not claim to reconstruct every tick.
        </p>
      </section>

      <section aria-labelledby="alert-execution" id="alert-execution">
        <h2 className="guide-heading">Confusing alerts with execution</h2>
        <p>
          An entry alert is a notification about a supported future signal. It
          is not an order, position, broker connection, paper-trading ledger, or
          TP/SL manager. Historical simulation is similarly hypothetical and
          owner-scoped.
        </p>
        <p>
          Keep the boundary clear with <Link href="/guides/backtesting-vs-forward-testing">backtesting versus forward testing</Link> and the product’s own assumptions.
        </p>
      </section>
    </>
  ),
};
