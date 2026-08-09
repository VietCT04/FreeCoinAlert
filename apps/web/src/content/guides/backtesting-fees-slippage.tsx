import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const backtestingFeesSlippageGuide: GuideArticle = {
  slug: "backtesting-fees-slippage",
  title: "How Fees and Slippage Change a Crypto Backtest",
  metaTitle: "How Fees and Slippage Change a Crypto Backtest",
  metaDescription:
    "Learn why gross price movement can become weaker net performance after modeled fees and adverse slippage in a crypto historical simulation.",
  summary:
    "Fees and slippage turn an idealized price path into a more conservative hypothetical fill model. Compare gross and net results only with the engine assumptions and trade frequency in view.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "gross-net", title: "Gross versus net" },
    { id: "model", title: "The model in the report" },
    { id: "impact", title: "Why small costs add up" },
    { id: "compare", title: "Compare like with like" },
    { id: "disclose", title: "Disclose the assumptions" },
  ],
  relatedGuideSlugs: ["crypto-take-profit-stop-loss", "common-backtesting-mistakes"],
  relatedLandingRoutes: [
    { href: "/crypto-backtesting", label: "Crypto backtesting workflow" },
    { href: "/tp-sl-backtest", label: "TP/SL backtest workflow" },
  ],
  body: (
    <>
      <section aria-labelledby="gross-net" id="gross-net">
        <h2 className="guide-heading">Gross versus net</h2>
        <p>
          Gross return describes the price change before modeled trading costs.
          Net return includes the engine’s fill adjustments and fees. Two
          strategies with the same gross movement can therefore produce
          different net outcomes when they trade at different frequencies or
          hold different distances to their exits.
        </p>
        <p>
          A net result is not automatically a forecast of account performance;
          it is the output of the selected historical assumptions.
        </p>
      </section>

      <section aria-labelledby="model" id="model">
        <h2 className="guide-heading">The model in the report</h2>
        <p>
          FreeCoinAlert’s historical engines keep fee and slippage assumptions
          server-controlled and versioned. The current fixed simulation models
          5 basis points of adverse slippage on entry and exit and 10 basis
          points of fee on each side; the configurable path preserves the same
          fill concepts while publishing its own immutable strategy and result
          version.
        </p>
        <p>
          Treat those numbers as product-engine assumptions, not as a claim
          about every exchange account, market, order type, or future fee
          schedule. The report’s methodology and version are the source of
          truth for the selected run.
        </p>
      </section>

      <section aria-labelledby="impact" id="impact">
        <h2 className="guide-heading">Why small costs add up</h2>
        <p>
          A round trip has an entry and an exit. A strategy that opens many
          positions pays that cost many times, and a narrow take-profit target
          leaves less room for slippage before the gross edge disappears.
          Compounding can magnify both positive and negative effects over a
          long sequence.
        </p>
        <GuideCallout title="A headline metric needs a cost context" tone="caution">
          <p>
            Do not compare a gross-only result with a net result as if they used
            the same execution model. Include the fee, slippage, range,
            timeframe, and trade count in the comparison.
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="compare" id="compare">
        <h2 className="guide-heading">Compare like with like</h2>
        <p>
          When comparing two reports, keep the market, timeframe, date range,
          entry version, exit rules, and engine assumptions aligned unless the
          purpose is specifically to study one of those changes. Record the
          immutable strategy and dataset fingerprints when reproducibility
          matters.
        </p>
        <p>
          For TP and SL fill details, read <Link href="/guides/crypto-take-profit-stop-loss">crypto take-profit and stop-loss backtesting</Link>.
        </p>
      </section>

      <section aria-labelledby="disclose" id="disclose">
        <h2 className="guide-heading">Disclose the assumptions</h2>
        <p>
          A responsible historical explanation states whether a number is gross
          or net, how fees and slippage were modeled, what data source was used,
          and which intrabar limitations remain. That context is more useful
          than presenting a single number without its calculation boundary.
        </p>
      </section>
    </>
  ),
};
