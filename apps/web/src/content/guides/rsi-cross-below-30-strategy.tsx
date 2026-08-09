import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const rsiCrossBelow30Guide: GuideArticle = {
  slug: "rsi-cross-below-30-strategy",
  title: "RSI Below 30 vs RSI Crosses Below 30",
  metaTitle: "RSI Below 30 vs RSI Crosses Below 30",
  metaDescription:
    "Understand the difference between RSI staying below 30 and crossing below 30, then test the supported entry with explicit historical exits.",
  summary:
    "RSI below 30 is a state; RSI crosses below 30 is a transition. The distinction changes when a supported historical entry is known and how repeated signals are avoided.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "below-versus-cross", title: "Below 30 versus crossing below 30" },
    { id: "supported-example", title: "A supported historical example" },
    { id: "when-entry-known", title: "When the entry is known" },
    { id: "explicit-exits", title: "Add explicit exits" },
    { id: "interpret-signal", title: "Interpret the signal carefully" },
  ],
  relatedGuideSlugs: ["rsi-backtesting", "backtesting-vs-forward-testing"],
  relatedLandingRoutes: [
    { href: "/rsi-backtest", label: "RSI backtest workflow" },
    { href: "/strategy-alerts", label: "Strategy entry alerts" },
  ],
  body: (
    <>
      <section aria-labelledby="below-versus-cross" id="below-versus-cross">
        <h2 className="guide-heading">Below 30 versus crossing below 30</h2>
        <p>
          “RSI below 30” is true whenever the current confirmed RSI value is
          below the threshold. “RSI crosses below 30” identifies a change from
          the prior side of the threshold to the current side. A state can last
          for several candles; a crossing is a particular transition.
        </p>
        <p>
          Treating every below-30 candle as a new entry can create repeated
          hypothetical positions. A crossing condition gives the entry a
          precise candle and lets the server apply its overlap and execution
          rules consistently.
        </p>
      </section>

      <section aria-labelledby="supported-example" id="supported-example">
        <h2 className="guide-heading">A supported historical example</h2>
        <p>
          One supported input can be written as:
        </p>
        <figure className="my-6 rounded-xl border bg-muted/30 p-5">
          <figcaption className="text-sm font-semibold">Example inputs</figcaption>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-muted-foreground">Market</dt><dd className="font-medium">BTCUSDT</dd></div>
            <div><dt className="text-muted-foreground">Timeframe</dt><dd className="font-medium">1H</dd></div>
            <div><dt className="text-muted-foreground">Entry</dt><dd className="font-medium">RSI(14) crosses below 30</dd></div>
            <div><dt className="text-muted-foreground">Exits</dt><dd className="font-medium">TP +6%, SL -3%, max holding 7 candles</dd></div>
          </dl>
        </figure>
        <p>
          These are inputs, not a claimed result. No return, win rate, or trade
          count should be inferred from the example without running a selected
          completed range.
        </p>
      </section>

      <section aria-labelledby="when-entry-known" id="when-entry-known">
        <h2 className="guide-heading">When the entry is known</h2>
        <p>
          The strategy evaluator uses confirmed candle closes. The signal is
          known at that close, and the historical engine schedules entry at the
          next candle open. This keeps future candle information out of the
          entry decision.
        </p>
        <GuideCallout title="A crossing is not a forecast" tone="caution">
          <p>
            Crossing below 30 says what RSI did relative to its threshold. It
            does not prove that price will rise, that a bottom has formed, or
            that a future trade will be profitable.
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="explicit-exits" id="explicit-exits">
        <h2 className="guide-heading">Add explicit exits</h2>
        <p>
          A signal condition is not a complete position plan. FreeCoinAlert’s
          configurable historical path supports a long-only plan with at most
          one take-profit percentage, one stop-loss percentage, one RSI
          threshold-cross exit, and one required maximum-holding rule.
        </p>
        <p>
          Stop loss, take profit, RSI exit, and maximum holding have a disclosed
          deterministic priority. Candle high/low data still cannot reveal the
          exact intrabar path when both price levels are touched.
        </p>
        <p>
          Read <Link href="/guides/crypto-take-profit-stop-loss">how TP and SL are tested</Link> before comparing two configurations.
        </p>
      </section>

      <section aria-labelledby="interpret-signal" id="interpret-signal">
        <h2 className="guide-heading">Interpret the signal carefully</h2>
        <p>
          Compare the result with its timeframe, date range, trade count,
          drawdown, costs, and strategy version. If you want to observe the same
          entry on future confirmed candles, an alert can monitor that entry
          condition. It does not carry the backtest’s exits into a live position
          or place an order.
        </p>
        <p>
          The difference between historical testing and future observation is
          covered in <Link href="/guides/backtesting-vs-forward-testing">backtesting versus forward testing</Link>.
        </p>
      </section>
    </>
  ),
};
