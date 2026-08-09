import Link from "next/link";

import { GuideCallout } from "../../components/marketing/guides/guide-callout";
import { GUIDE_FIRST_PUBLISHED } from "./guide-date";
import type { GuideArticle } from "./types";

export const howToBacktestCryptoStrategyGuide: GuideArticle = {
  slug: "how-to-backtest-crypto-strategy",
  title: "How to Backtest a Crypto Strategy",
  metaTitle: "How to Backtest a Crypto Strategy",
  metaDescription:
    "A practical guide to defining a crypto strategy, choosing historical candles, reading backtest results, and avoiding look-ahead bias.",
  summary:
    "A useful crypto backtest starts with a precise question, a supported entry and exit plan, and a completed UTC candle range. It ends with a cautious reading of risk and trade count, not a promise about the future.",
  publishedAt: GUIDE_FIRST_PUBLISHED,
  updatedAt: GUIDE_FIRST_PUBLISHED,
  author: "FreeCoinAlert",
  historicalSimulation: true,
  sections: [
    { id: "define-question", title: "Define the question first" },
    { id: "choose-market-timeframe", title: "Choose a market and timeframe" },
    { id: "define-entry", title: "Define a supported entry" },
    { id: "define-exits", title: "Define exits and assumptions" },
    { id: "choose-range", title: "Choose a completed UTC range" },
    { id: "run-simulation", title: "Run and read the simulation" },
    { id: "avoid-overfitting", title: "Avoid overfitting" },
    { id: "monitor-entry", title: "Optionally monitor the entry" },
  ],
  relatedGuideSlugs: [
    "rsi-backtesting",
    "crypto-take-profit-stop-loss",
    "common-backtesting-mistakes",
  ],
  relatedLandingRoutes: [
    { href: "/crypto-backtesting", label: "Crypto backtesting workflow" },
    { href: "/crypto-strategy-tester", label: "Crypto strategy tester" },
  ],
  body: (
    <>
      <section aria-labelledby="define-question" id="define-question">
        <h2 className="guide-heading">1. Define the question first</h2>
        <p>
          Start by writing down what you want to learn before looking at any
          output. For example: “What would have happened if this supported RSI
          entry had been evaluated on BTCUSDT 1H over this completed range?”
          That question is narrower and more useful than asking whether a
          strategy is “the best.”
        </p>
        <p>
          Record the market, timeframe, entry condition, exit rules, date
          range, and execution assumptions. Changing any of them changes the
          historical experiment.
        </p>
      </section>

      <section aria-labelledby="choose-market-timeframe" id="choose-market-timeframe">
        <h2 className="guide-heading">2. Choose a market and timeframe</h2>
        <p>
          FreeCoinAlert uses a controlled Binance Spot catalogue and stored
          complete candles. Historical analysis currently supports the fixed
          preset timeframes of 1 hour and 4 hours, with a bounded UTC range.
          The available market and preset choices come from the server rather
          than from an arbitrary symbol field.
        </p>
        <p>
          A 1-hour result and a 4-hour result are different experiments. Do not
          compare them as if they were the same sampling of price movement.
        </p>
      </section>

      <section aria-labelledby="define-entry" id="define-entry">
        <h2 className="guide-heading">3. Define a supported entry</h2>
        <p>
          The current product supports versioned price/SMA 200 crossings and
          Wilder RSI 14 threshold crossings. The server pins the preset,
          direction, calculation version, and close-price input. The browser
          does not submit formulas or arbitrary indicator code.
        </p>
        <p>
          A concrete input example is <strong>BTCUSDT · 1H · RSI crosses below
          30</strong>. That is an entry condition, not a claim that price will
          rise after the crossing.
        </p>
        <p>
          See the focused explanations for <Link href="/guides/rsi-backtesting">RSI backtesting</Link> and <Link href="/guides/sma-crossover-backtesting">SMA crossover backtesting</Link>.
        </p>
      </section>

      <section aria-labelledby="define-exits" id="define-exits">
        <h2 className="guide-heading">4. Define exits and assumptions</h2>
        <p>
          A strategy is more than its entry. Configurable historical analysis
          accepts supported long-only take-profit, stop-loss, RSI threshold
          cross, and maximum-holding rules. Maximum holding is required, and
          the server validates the number and range of rules.
        </p>
        <p>
          Exit ordering matters when more than one rule could apply on the same
          candle. FreeCoinAlert discloses its deterministic order and uses
          candle high/low observations under bounded assumptions. Read the <Link href="/guides/crypto-take-profit-stop-loss">TP/SL guide</Link> before treating a result as precise intrabar history.
        </p>
      </section>

      <section aria-labelledby="choose-range" id="choose-range">
        <h2 className="guide-heading">5. Choose a completed UTC range</h2>
        <p>
          Use a start-inclusive, end-exclusive range whose final boundary is a
          fully closed candle boundary. The worker validates contiguous stored
          history and includes the warm-up candles needed by the selected
          calculation outside the visible analysis range.
        </p>
        <p>
          Missing candles are not silently filled in the browser. A range with
          insufficient or gapped canonical coverage fails safely instead of
          producing a partial answer.
        </p>
      </section>

      <section aria-labelledby="run-simulation" id="run-simulation">
        <h2 className="guide-heading">6. Run and read the simulation</h2>
        <p>
          The separate historical-analysis worker reads an immutable snapshot
          of stored candles and runs a versioned, provider-neutral simulation.
          The report exposes server-provided return, maximum drawdown, win
          rate, profit factor, trade count, trades, and equity points.
        </p>
        <ul>
          <li><strong>Return</strong> describes the simulated change in equity under the stated assumptions.</li>
          <li><strong>Maximum drawdown</strong> shows the largest peak-to-trough decline in the simulated equity path.</li>
          <li><strong>Win rate</strong> describes the share of completed simulated trades with a positive result.</li>
          <li><strong>Profit factor</strong> compares gross simulated gains with gross simulated losses when those values are defined.</li>
          <li><strong>Trade count</strong> tells you how much evidence the selected range produced; it is not a confidence score.</li>
        </ul>
        <GuideCallout title="Use the assumptions with the metrics" tone="caution">
          <p>
            A metric without its market, timeframe, date range, strategy
            version, costs, slippage, and sample size is incomplete context.
            FreeCoinAlert keeps those disclosures with the owner-scoped report.
          </p>
        </GuideCallout>
      </section>

      <section aria-labelledby="avoid-overfitting" id="avoid-overfitting">
        <h2 className="guide-heading">7. Avoid overfitting and prediction language</h2>
        <p>
          Trying many thresholds, markets, ranges, and exit rules until one
          historical result looks attractive can overfit the selected sample.
          Keep the question and rules fixed, reserve a separate future period
          for forward observation, and treat a single report as one historical
          scenario rather than proof.
        </p>
        <p>
          Historical analysis cannot remove market uncertainty. It is a way to
          make assumptions explicit and inspect their consequences on stored
          data.
        </p>
      </section>

      <section aria-labelledby="monitor-entry" id="monitor-entry">
        <h2 className="guide-heading">8. Optionally monitor the entry</h2>
        <p>
          After inspecting a report, the supported next step is to monitor the
          same entry condition for a future confirmed candle signal. That alert
          is informational and does not track the backtest’s TP, SL, maximum
          holding period, position, or profit-and-loss outcome.
        </p>
        <p>
          Alerts notify about supported entry signals; they do not place or
          manage trades. Compare the distinction in <Link href="/guides/backtesting-vs-forward-testing">backtesting versus forward testing</Link>.
        </p>
      </section>
    </>
  ),
};
