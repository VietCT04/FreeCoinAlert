import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const backtestingVsForwardTestingGuide: GuideArticle = {
  slug: "backtesting-vs-forward-testing",
  title: "Backtesting vs Forward Testing for Crypto Strategies",
  metaTitle: "Backtesting vs Forward Testing for Crypto Strategies",
  metaDescription:
    "Compare historical hypothetical backtesting, forward observation on future data, and live entry-signal alerts without confusing alerts with execution.",
  summary:
    "Backtesting asks what a defined strategy would have done on historical candles. Forward testing observes future data without rewriting history. FreeCoinAlert bridges the first to entry alerts, not to live position management.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "three-meanings", title: "Three different activities" },
    { id: "workflow", title: "A careful workflow" },
    { id: "what-alert-does", title: "What an entry alert does" },
    { id: "what-not-supported", title: "What is not supported" },
  ],
  relatedGuideSlugs: ["how-to-backtest-crypto-strategy", "common-backtesting-mistakes"],
  relatedLandingRoutes: [
    { href: "/crypto-backtesting", label: "Crypto backtesting workflow" },
    { href: "/strategy-alerts", label: "Strategy entry alerts" },
  ],
  body: (
    <>
      <section aria-labelledby="three-meanings" id="three-meanings">
        <h2 className="guide-heading">Three different activities</h2>
        <dl className="space-y-5">
          <div>
            <dt className="font-semibold">Backtest</dt>
            <dd className="text-muted-foreground">
              Run a versioned, hypothetical simulation over completed stored
              candles with explicit execution assumptions.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">Forward test</dt>
            <dd className="text-muted-foreground">
              Observe the same rules on future or live data after the historical
              range, without changing the past report.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">Live entry monitoring</dt>
            <dd className="text-muted-foreground">
              Receive an informational alert when a supported entry condition is
              detected on a future confirmed candle.
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="workflow" id="workflow">
        <h2 className="guide-heading">A careful workflow</h2>
        <ol>
          <li>Define the market, timeframe, entry, exits, and costs before reading results.</li>
          <li>Run the historical simulation on a completed UTC range.</li>
          <li>Record the strategy version, sample size, drawdown, and assumptions.</li>
          <li>Reserve a later period for observation rather than repeatedly tuning the original range.</li>
          <li>Compare future observations with the same rules and document any approved version change.</li>
        </ol>
        <p>
          This workflow does not guarantee that a historical relationship will
          continue. It reduces ambiguity about what was tested and what was
          observed later.
        </p>
      </section>

      <section aria-labelledby="what-alert-does" id="what-alert-does">
        <h2 className="guide-heading">What an entry alert does</h2>
        <p>
          FreeCoinAlert can monitor a supported entry condition, such as RSI 14
          crossing below 30 or price crossing SMA 200, and deliver an alert via
          the existing Telegram destination flow when the server detects the
          condition.
        </p>
        <GuideCallout title="The alert is narrower than the backtest">
          <p>
            An entry alert does not carry TP, SL, maximum holding, hypothetical
            equity, or PnL from the historical report. It does not open, manage,
            or close a position.
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="what-not-supported" id="what-not-supported">
        <h2 className="guide-heading">What is not supported</h2>
        <p>
          FreeCoinAlert does not provide a paper-trading ledger, live position
          engine, automated trading, exchange API-key integration, or public
          report sharing. It is an informational product with owner-scoped
          historical reports and supported future signal alerts.
        </p>
        <p>
          See <Link href="/guides/common-backtesting-mistakes">common backtesting mistakes</Link> for ways to keep these boundaries clear when evaluating results.
        </p>
      </section>
    </>
  ),
};
