import { createPublicMetadata } from "@/lib/seo/metadata";

export type SeoLandingSection = {
  id: string;
  heading: string;
  paragraphs: readonly string[];
  bullets?: readonly string[];
};

export type SeoLandingExample = {
  heading: string;
  intro: string;
  label: string;
  rows: readonly { label: string; value: string }[];
  note: string;
};

export type SeoLandingFaq = {
  question: string;
  answer: string;
};

export type SeoLandingPage = {
  slug: string;
  path: string;
  title: string;
  description: string;
  h1: string;
  intro: string;
  primaryIntent: string;
  sections: readonly SeoLandingSection[];
  example?: SeoLandingExample;
  limitations: readonly string[];
  relatedPages: readonly { href: string; label: string }[];
  cta: { heading: string; body: string };
  faqs?: readonly SeoLandingFaq[];
};

const pages: Record<string, SeoLandingPage> = {
  "/crypto-backtesting": {
    slug: "crypto-backtesting",
    path: "/crypto-backtesting",
    title: "Free Crypto Backtesting Tool",
    description:
      "Backtest supported crypto entry and exit rules on stored Binance Spot candles, then inspect hypothetical trades, risk metrics, and assumptions.",
    h1: "Backtest Crypto Strategies on Historical Market Data",
    intro:
      "FreeCoinAlert lets you test a supported crypto strategy against stored, confirmed candles. Choose an entry preset, configure the available exits, and read an immutable report without turning historical results into a promise about the future.",
    primaryIntent: "Crypto backtesting",
    sections: [
      {
        id: "workflow",
        heading: "From strategy rules to an immutable report",
        paragraphs: [
          "The historical-analysis workflow records the selected market, timeframe, entry preset, exit rules, date range, and server-owned assumptions before the worker runs the simulation. The resulting report preserves those inputs so a result can be understood later rather than inferred from a mutable UI.",
          "The simulation uses stored platform candles after coverage validation. It does not query Binance separately for each request, and it remains separate from live signal evaluation, Telegram delivery, and trading execution.",
        ],
      },
      {
        id: "execution",
        heading: "Execution assumptions are part of the test",
        paragraphs: [
          "Entry signals are confirmed on a closed candle and a hypothetical position enters at the next candle open. Fees and adverse slippage are applied using the configured execution model, and only one hypothetical position uses current equity at a time.",
          "When OHLC data cannot reveal which intrabar level happened first, the configurable engine uses the documented conservative order: stop loss, take profit, RSI exit, then maximum holding.",
        ],
      },
      {
        id: "metrics",
        heading: "Read more than one performance number",
        paragraphs: [
          "A report can include net return, maximum drawdown, win rate, profit factor, trade count, exit reasons, hypothetical trade details, an entry/exit price chart, and equity progression. These are descriptions of the selected historical sample, not predictions or recommendations.",
          "A useful review asks whether the range has complete coverage, whether the sample contains enough trades to be informative, and whether the assumptions match the question being asked.",
        ],
      },
    ],
    limitations: [
      "The catalogue is controlled Binance Spot USDT markets, not every exchange, venue, or coin.",
      "Only supported fixed entry presets and approved configurable exits can be selected.",
      "A historical simulation cannot reveal future prices or guarantee delivery, profit, or execution.",
      "Gaps or insufficient stored candles prevent a result instead of being silently filled.",
    ],
    relatedPages: [
      { href: "/crypto-strategy-tester", label: "Build a crypto strategy test" },
      { href: "/rsi-backtest", label: "Backtest RSI strategies" },
      { href: "/sma-backtest", label: "Backtest price and SMA crosses" },
      { href: "/tp-sl-backtest", label: "Understand TP and SL backtesting" },
    ],
    cta: {
      heading: "Test a supported strategy",
      body: "Build a strategy, backtest it on stored candles, and inspect the assumptions behind the result.",
    },
  },
  "/crypto-strategy-tester": {
    slug: "crypto-strategy-tester",
    path: "/crypto-strategy-tester",
    title: "Crypto Strategy Tester for Entry and Exit Rules",
    description:
      "Build a supported crypto strategy from an entry preset, long position, exit rules, and a historical period, then run a deterministic historical test.",
    h1: "Build and Test a Crypto Trading Strategy",
    intro:
      "A strategy test starts with a defined entry and a defined exit plan. FreeCoinAlert provides a constrained builder for supported presets and long-only configurable exits, so the report describes exactly what was tested.",
    primaryIntent: "Crypto strategy tester",
    sections: [
      {
        id: "builder",
        heading: "Assemble a strategy from supported pieces",
        paragraphs: [
          "Choose a server-provided entry preset, keep the selected timeframe and direction, add the exits that the platform supports, and select a UTC analysis period. The server validates the combination and stores a versioned strategy snapshot before work is queued.",
          "This is a strategy construction workflow, not a code editor. You cannot submit arbitrary formulas, Pine Script, custom indicators, or unbounded customer-authored code.",
        ],
      },
      {
        id: "determinism",
        heading: "The same inputs keep the same meaning",
        paragraphs: [
          "The report identifies the preset version, calculation version, engine version, assumptions, data coverage, and strategy fingerprint. That makes the output traceable to the rules and candle snapshot used for the run.",
          "Entry calculations use confirmed closed candles. A qualifying entry schedules the next candle open, and overlapping signals are ignored while a hypothetical position is open.",
        ],
      },
      {
        id: "review",
        heading: "Review the test as a set of assumptions",
        paragraphs: [
          "The result shows risk and outcome context together: net return, maximum drawdown, win rate, profit factor, trades, exit reasons, equity progression, and price markers. Undefined metrics remain explicitly undefined when a sample has no trades or no losing trades.",
          "The purpose is to understand how a rule behaved over a bounded historical range, not to rank strategies or claim that one configuration will perform best next.",
        ],
      },
    ],
    example: {
      heading: "A supported builder-style example",
      intro: "This is a valid configuration shape, shown without fabricated performance figures.",
      label: "Example configuration",
      rows: [
        { label: "Entry preset", value: "RSI(14) crosses below 30" },
        { label: "Position", value: "Long" },
        { label: "Exits", value: "TP +6%, SL -3%, max 7 candles" },
        { label: "Timeframe", value: "1H or 4H preset timeframe" },
        { label: "Entry execution", value: "Next candle open" },
      ],
      note: "Example configuration — not a performance claim.",
    },
    limitations: [
      "The builder exposes server-controlled presets and exit rules only.",
      "Configurable execution is long-only; it is not a live order or short-trading system.",
      "The historical range must have complete canonical candle coverage.",
      "Results are hypothetical and do not predict future market behavior.",
    ],
    relatedPages: [
      { href: "/crypto-backtesting", label: "See the crypto backtesting workflow" },
      { href: "/tp-sl-backtest", label: "Test take-profit and stop-loss rules" },
      { href: "/strategy-alerts", label: "Learn about entry monitoring after a test" },
    ],
    cta: {
      heading: "Build your test from supported rules",
      body: "Choose the entry, exits, period, and assumptions that make your historical question precise.",
    },
  },
  "/bitcoin-backtest": {
    slug: "bitcoin-backtest",
    path: "/bitcoin-backtest",
    title: "Bitcoin Strategy Backtesting",
    description:
      "Backtest supported BTCUSDT entry and exit configurations on stored Binance Spot candles with explicit execution and historical-data assumptions.",
    h1: "Backtest Bitcoin Trading Strategies",
    intro:
      "Use the controlled FreeCoinAlert BTCUSDT market to study supported strategy rules over stored Binance Spot candles. This page is about market-data backtesting for BTC/USDT, not Bitcoin network activity or every Bitcoin trading venue.",
    primaryIntent: "Bitcoin backtest",
    sections: [
      {
        id: "market",
        heading: "What Bitcoin backtesting means here",
        paragraphs: [
          "FreeCoinAlert’s Bitcoin example uses BTCUSDT from its validated Binance Spot catalogue. The report is built from canonical stored candles for the selected 1h or 4h preset timeframe after the server checks continuity and coverage.",
          "It does not represent futures, options, leverage, on-chain data, order-book simulation, or all venues where BTC trades.",
        ],
      },
      {
        id: "example",
        heading: "Study a precise BTCUSDT question",
        paragraphs: [
          "A useful test states the entry condition, position direction, exit rules, range, and execution assumptions together. Changing the timeframe or exit rule changes the historical question and should produce a separately understood report.",
          "The worker uses confirmed candles and schedules a qualifying entry at the next candle open. It does not use a future candle to decide whether an earlier entry existed.",
        ],
      },
      {
        id: "report",
        heading: "Inspect the historical result",
        paragraphs: [
          "Review drawdown and trade outcomes alongside net return, rather than treating one number as a recommendation. The report includes server-provided trade markers, equity progression, exit reasons, data coverage, and the assumptions that define the simulation.",
          "A BTCUSDT backtest remains a bounded hypothetical sample. It says how the documented rules behaved on that stored range, not what BTC will do next.",
        ],
      },
    ],
    example: {
      heading: "Example BTCUSDT configuration",
      intro: "This demonstrates a supported long configuration; it contains no historical performance claim.",
      label: "Example configuration",
      rows: [
        { label: "Market", value: "BTCUSDT · Binance Spot" },
        { label: "Timeframe", value: "4H" },
        { label: "Entry", value: "RSI(14) crosses below 30" },
        { label: "Exits", value: "TP +6%, SL -3%, max 7 candles" },
        { label: "Position", value: "Long" },
      ],
      note: "Example configuration — not a performance claim.",
    },
    limitations: [
      "BTCUSDT is one controlled Binance Spot market, not a proxy for every BTC venue.",
      "The example does not include leverage, futures, options, or on-chain signals.",
      "Stored-candle coverage and the selected range bound the result.",
      "Historical BTC behavior is not a prediction or an investment recommendation.",
    ],
    relatedPages: [
      { href: "/crypto-backtesting", label: "Read the broad crypto backtesting workflow" },
      { href: "/rsi-backtest", label: "Understand the RSI entry example" },
      { href: "/strategy-alerts", label: "Monitor a supported BTC entry later" },
    ],
    cta: {
      heading: "Test a BTCUSDT strategy question",
      body: "Choose a supported BTCUSDT entry and exit configuration, then inspect its historical assumptions and report.",
    },
  },
  "/rsi-backtest": {
    slug: "rsi-backtest",
    path: "/rsi-backtest",
    title: "RSI Crypto Strategy Backtesting",
    description:
      "Backtest the supported Wilder RSI(14) close-based threshold-cross entries and exits on historical crypto candles without inventing custom RSI formulas.",
    h1: "Backtest RSI Strategies on Crypto",
    intro:
      "FreeCoinAlert uses a versioned Wilder RSI(14) calculation over confirmed close prices. Test the supported threshold-cross entries and approved RSI exit rule while keeping the difference between a crossing and a static threshold clear.",
    primaryIntent: "RSI backtest",
    sections: [
      {
        id: "model",
        heading: "The implemented RSI model",
        paragraphs: [
          "The current catalog uses Wilder RSI with period 14 and close-price input. Supported entry presets include RSI(14) crossing below 30 and crossing above 70 on the preset timeframes where those versions are available.",
          "A crossing is an event between the previous and current confirmed values. “RSI below 30” describes a state; “RSI crosses below 30” describes the transition into that state. The platform evaluates the defined event, not a custom interpretation from the browser.",
        ],
      },
      {
        id: "exits",
        heading: "Pair the entry with approved exits",
        paragraphs: [
          "A configurable long test can add a take-profit percentage, stop-loss percentage, optional RSI threshold-cross exit, and maximum-holding rule. The server pins the RSI exit to RSI(14), close input, the selected entry timeframe, and its calculation version.",
          "The entry is confirmed at candle close and a qualifying position enters at the next candle open. The browser does not calculate RSI, metrics, or trade results.",
        ],
      },
      {
        id: "interpretation",
        heading: "Interpret an RSI result carefully",
        paragraphs: [
          "Inspect sample size, drawdown, exit reasons, and the exact date range with net return and win rate. A threshold-cross backtest is a historical hypothetical simulation under its stated assumptions, not evidence that RSI predicts price direction.",
          "The report records the calculation and strategy versions so a later catalog change cannot silently rewrite what the original test meant.",
        ],
      },
    ],
    example: {
      heading: "Example RSI configuration",
      intro: "This shows supported vocabulary rather than a claimed winning setup.",
      label: "Example configuration",
      rows: [
        { label: "Entry", value: "Wilder RSI(14) crosses below 30" },
        { label: "Input", value: "Confirmed close" },
        { label: "Position", value: "Long" },
        { label: "Optional exit", value: "RSI threshold cross" },
        { label: "Timeframe", value: "1H or 4H" },
      ],
      note: "Example configuration — not a performance claim.",
    },
    limitations: [
      "RSI period, formula, and input are versioned server-owned values.",
      "The page does not offer arbitrary RSI periods, custom formulas, or intrabar evaluation.",
      "A confirmed threshold crossing does not predict the next price movement.",
      "The result is limited to supported markets, timeframes, stored data, and selected exits.",
    ],
    relatedPages: [
      { href: "/crypto-strategy-tester", label: "Build an RSI strategy test" },
      { href: "/tp-sl-backtest", label: "Add context for TP and SL exits" },
      { href: "/strategy-alerts", label: "Monitor an RSI entry condition" },
    ],
    cta: {
      heading: "Test a supported RSI event",
      body: "Use the versioned RSI(14) entry and approved exit controls to ask a precise historical question.",
    },
  },
  "/sma-backtest": {
    slug: "sma-backtest",
    path: "/sma-backtest",
    title: "SMA Crossover Crypto Backtesting",
    description:
      "Backtest FreeCoinAlert’s supported price-versus-SMA(200) close crossover entries on historical crypto candles with explicit assumptions.",
    h1: "Backtest Crypto Price and SMA Crossover Strategies",
    intro:
      "Study the supported price-versus-SMA(200) crossing presets on complete historical candles. FreeCoinAlert keeps the current MVP focused: this is not an arbitrary fast/slow moving-average strategy builder.",
    primaryIntent: "SMA crossover backtest",
    sections: [
      {
        id: "semantics",
        heading: "Price versus SMA is the current entry model",
        paragraphs: [
          "The catalog contains versioned price crossing SMA(200) presets using close input on the supported preset timeframes. The event compares the previous and current confirmed values with the platform’s equality-aware crossing rules.",
          "That is different from a fast-SMA/slow-SMA crossover system. The current product does not expose arbitrary moving-average periods, multiple indicator combinations, or custom formulas.",
        ],
      },
      {
        id: "execution",
        heading: "Test the event with stated execution rules",
        paragraphs: [
          "The signal is evaluated after the candle closes, and a qualifying hypothetical entry uses the next candle open. You can pair the supported entry with approved long-only TP, SL, RSI, and maximum-holding exits.",
          "The report keeps the preset code, calculation version, dataset coverage, and assumptions with the result so the event is not confused with a different moving-average definition.",
        ],
      },
      {
        id: "review",
        heading: "Do not reduce a crossover test to win rate",
        paragraphs: [
          "Review net return, maximum drawdown, profit factor, trades, exit reasons, and the exact date range together. A zero-trade result remains meaningful as a statement about that range, not a reason to invent a performance metric.",
          "As with every historical report, an SMA crossing describes past behavior under a hypothetical model. It does not predict future price movement or place orders.",
        ],
      },
    ],
    example: {
      heading: "Example SMA configuration",
      intro: "This uses the current supported price-versus-SMA entry semantics.",
      label: "Example configuration",
      rows: [
        { label: "Entry", value: "Price crosses above SMA(200)" },
        { label: "Input", value: "Confirmed close" },
        { label: "Position", value: "Long" },
        { label: "Exits", value: "TP, SL, RSI cross, or max holding" },
        { label: "Timeframe", value: "Supported 1H or 4H preset" },
      ],
      note: "Example configuration — not a performance claim.",
    },
    limitations: [
      "The current entry catalog is price versus SMA(200), not arbitrary fast/slow SMA pairs.",
      "The browser cannot submit custom formulas or moving-average periods.",
      "Signals use complete closed candles and next-open entry semantics.",
      "A historical crossover result is hypothetical and not a trading recommendation.",
    ],
    relatedPages: [
      { href: "/crypto-strategy-tester", label: "Build a supported strategy test" },
      { href: "/tp-sl-backtest", label: "Understand configurable exits" },
      { href: "/strategy-alerts", label: "Monitor a supported entry signal" },
    ],
    cta: {
      heading: "Test a price/SMA crossing",
      body: "Select the server-provided SMA(200) entry and review its historical behavior with explicit exits and assumptions.",
    },
  },
  "/tp-sl-backtest": {
    slug: "tp-sl-backtest",
    path: "/tp-sl-backtest",
    title: "Take-Profit and Stop-Loss Crypto Backtesting",
    description:
      "Understand how supported take-profit and stop-loss percentages, gaps, fees, slippage, and same-candle priority affect a crypto backtest.",
    h1: "Test Take-Profit and Stop-Loss Rules in Crypto Backtests",
    intro:
      "Take-profit and stop-loss settings only make sense when their fill assumptions are explicit. FreeCoinAlert documents how the configurable long-only simulation applies percentage levels, gaps, intrabar ambiguity, fees, and slippage.",
    primaryIntent: "TP and SL backtesting",
    sections: [
      {
        id: "levels",
        heading: "Levels are relative to the hypothetical entry",
        paragraphs: [
          "A take-profit percentage sets a level above the raw long entry price, while a stop-loss percentage sets a level below it. The engine evaluates those levels on each holding candle after the entry is scheduled at the next candle open.",
          "If a candle opens beyond a stop-loss level, the available open is used for the gap exit. Otherwise a low touching the level uses the stop-loss level. Take profit uses a high touching its level.",
        ],
      },
      {
        id: "ambiguity",
        heading: "OHLC candles cannot show every intrabar order",
        paragraphs: [
          "A single candle can contain both a stop-loss low and a take-profit high, but OHLC data does not reveal which occurred first. FreeCoinAlert uses a conservative same-candle priority: stop loss, take profit, RSI indicator exit, then maximum holding.",
          "That rule is part of the report’s assumptions. It is not a claim that the exchange would have filled a live order in the same way.",
        ],
      },
      {
        id: "costs",
        heading: "Costs are applied after raw price determination",
        paragraphs: [
          "The engine determines the raw entry or exit price from the candle and exit rule first. It then applies adverse entry and exit slippage plus the configured fees to the fill values and compounds the resulting equity into the next position.",
          "The report exposes the exit reason and price basis so the result is not reduced to a hidden percentage calculation.",
        ],
      },
    ],
    example: {
      heading: "Example exit plan",
      intro: "The percentages are an example configuration, not a promised outcome.",
      label: "Example configuration",
      rows: [
        { label: "Position", value: "Long" },
        { label: "Take profit", value: "+6% from raw entry" },
        { label: "Stop loss", value: "−3% from raw entry" },
        { label: "Additional exits", value: "RSI cross and max holding" },
        { label: "Same candle", value: "SL → TP → indicator → max holding" },
      ],
      note: "Example configuration — not a performance claim.",
    },
    limitations: [
      "Configurable TP/SL simulation is long-only and hypothetical.",
      "OHLC data cannot establish the true order of intrabar highs and lows.",
      "Fees and slippage are model assumptions, not a live execution guarantee.",
      "The platform does not turn these historical exit rules into live orders.",
    ],
    relatedPages: [
      { href: "/crypto-backtesting", label: "Read the full backtesting workflow" },
      { href: "/crypto-strategy-tester", label: "Build an entry and exit test" },
    ],
    cta: {
      heading: "Make your exit assumptions explicit",
      body: "Test supported TP and SL rules together with the entry, range, costs, and priority rules that define the simulation.",
    },
  },
  "/strategy-alerts": {
    slug: "strategy-alerts",
    path: "/strategy-alerts",
    title: "Crypto Strategy Entry Alerts After Backtesting",
    description:
      "Backtest a supported crypto strategy, then monitor the same entry condition with informational Telegram alerts without live trading or TP/SL execution.",
    h1: "Backtest a Crypto Strategy, Then Monitor Its Entry",
    intro:
      "A historical strategy can include an entry and an exit plan. Live monitoring is narrower: FreeCoinAlert can notify you when a supported entry condition occurs again, while leaving historical exits and trading execution out of the live alert.",
    primaryIntent: "Crypto strategy entry alerts",
    sections: [
      {
        id: "bridge",
        heading: "Keep the historical and live meanings separate",
        paragraphs: [
          "The backtest records the entry preset, exit rules, period, and historical result. The live path monitors the supported entry preset only. It does not carry the historical TP, SL, RSI exit, or maximum-holding plan into an automated position.",
          "This boundary prevents an informational entry alert from being mistaken for an order, a position tracker, or a guarantee that the backtest will repeat.",
        ],
      },
      {
        id: "notification",
        heading: "Telegram is a delivery destination, not an execution venue",
        paragraphs: [
          "After authentication and Telegram connection, an eligible entry signal can be delivered through the existing notification flow. The service checks ownership, subscription, occurrence, and destination readiness before sending.",
          "Delivery remains best-effort and subject to connection and provider status. The product does not request exchange API keys, place trades, or hold funds.",
        ],
      },
      {
        id: "workflow",
        heading: "A practical sequence",
        paragraphs: [
          "Start by testing a supported entry and exit configuration over a bounded historical range. Inspect the report’s assumptions and sample size. If the entry condition is useful for your monitoring question, use the supported entry-alert flow and connect Telegram when you want notifications.",
          "The alert’s message describes the entry occurrence. It does not report a live TP/SL position, live PnL, or a synthetic historical trade.",
        ],
      },
    ],
    example: {
      heading: "The product boundary in one example",
      intro: "The historical plan and live alert answer different questions.",
      label: "Example configuration",
      rows: [
        { label: "Historical test", value: "RSI(14) entry + TP/SL + max holding" },
        { label: "Live monitoring", value: "The supported RSI entry preset" },
        { label: "Notification", value: "Telegram when the entry occurs again" },
        { label: "Execution", value: "No live order is placed" },
      ],
      note: "The live alert does not track the historical exit plan.",
    },
    limitations: [
      "Only supported entry presets can be monitored; arbitrary user-authored rules are not accepted.",
      "Live alerts do not execute trades or track the historical TP/SL/max-holding plan.",
      "Telegram delivery depends on connection, consent, provider, and worker status.",
      "An alert occurrence is not a prediction, investment recommendation, or profit guarantee.",
    ],
    relatedPages: [
      { href: "/crypto-backtesting", label: "Start with the backtesting workflow" },
      { href: "/crypto-strategy-tester", label: "Build the entry and exit plan" },
      { href: "/rsi-backtest", label: "Explore RSI entry semantics" },
    ],
    cta: {
      heading: "Backtest first, then monitor the entry",
      body: "Understand the historical rule and its assumptions before choosing whether the supported entry condition is worth monitoring.",
    },
    faqs: [
      {
        question: "Does the alert place a trade?",
        answer:
          "No. FreeCoinAlert is an informational alert product. It does not request exchange API keys, place orders, or hold customer funds.",
      },
      {
        question: "Does live monitoring use my historical TP and SL?",
        answer:
          "No. The live path monitors the supported entry preset only. Historical exit rules remain part of the hypothetical report.",
      },
      {
        question: "Can Telegram delivery be guaranteed?",
        answer:
          "No. Delivery depends on Telegram readiness and the existing outbox and worker flow, so the product does not guarantee delivery.",
      },
    ],
  },
};

export const LANDING_PAGE_PATHS = Object.keys(pages) as readonly string[];

export function getSeoLandingPage(path: string): SeoLandingPage {
  const page = pages[path];

  if (!page) {
    throw new Error(`Unknown SEO landing page: ${path}`);
  }

  return page;
}

export function getSeoLandingMetadata(path: string) {
  const page = getSeoLandingPage(path);

  return createPublicMetadata({
    title: page.title,
    description: page.description,
    canonicalPath: page.path,
  });
}
