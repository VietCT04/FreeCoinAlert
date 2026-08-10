export type HomepageFlowStage = {
  number: string;
  title: string;
  description: string;
};

export const homepageFlowStages = [
  {
    number: "01",
    title: "Define the rules",
    description:
      "Choose a supported entry preset, timeframe, position direction, and exit plan.",
  },
  {
    number: "02",
    title: "Backtest and understand",
    description:
      "Run the rules against stored historical candles and inspect the report in context.",
  },
  {
    number: "03",
    title: "Monitor the entry",
    description:
      "Watch for the supported entry condition again when you are ready to receive an alert.",
  },
] satisfies readonly HomepageFlowStage[];

export type DifferentiationReason = {
  title: string;
  description: string;
};

export const differentiationReasons = [
  {
    title: "Test before monitoring",
    description:
      "Validate an entry idea against historical data before deciding to watch it.",
  },
  {
    title: "Transparent execution assumptions",
    description:
      "Entry timing, fees, slippage, position rules, and exit priority stay visible.",
  },
  {
    title: "No trading permissions",
    description:
      "FreeCoinAlert monitors and alerts; it does not need exchange order permissions or execute trades.",
  },
] satisfies readonly DifferentiationReason[];

export type MethodologyAssumption = {
  label: string;
  value: string;
};

export const methodologyAssumptions = [
  {
    label: "Signal timing",
    value: "Confirmed candle close",
  },
  {
    label: "Entry timing",
    value: "Next candle open",
  },
  {
    label: "Fees",
    value: "Modeled per side",
  },
  {
    label: "Slippage",
    value: "Adverse slippage modeled",
  },
  {
    label: "Position sizing",
    value: "One position / full-equity simulation",
  },
  {
    label: "Overlapping entries",
    value: "Ignored while a position is open",
  },
  {
    label: "Same-candle exits",
    value: "Documented conservative priority",
  },
  {
    label: "End of range",
    value: "Open position marked to market under the current simulation version",
  },
] satisfies readonly MethodologyAssumption[];

export type HomepageFaq = {
  question: string;
  answer: string;
};

export const homepageFaqs = [
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
      "Yes. Supported configurable strategies can include take-profit, stop-loss, indicator, and maximum-holding exits. The report explains the execution assumptions used.",
  },
  {
    question: "What happens if TP and SL are touched in the same candle?",
    answer:
      "The server uses a documented conservative priority so the result remains deterministic rather than choosing the more favorable outcome.",
  },
  {
    question: "What does live monitoring actually monitor?",
    answer:
      "Live monitoring watches the supported entry preset only. It does not turn historical take-profit, stop-loss, or holding-period rules into live positions or trade execution.",
  },
] satisfies readonly HomepageFaq[];

export const homepageExampleLinks = [
  { href: "/rsi-backtest", label: "RSI backtest" },
  { href: "/sma-backtest", label: "SMA backtest" },
  { href: "/tp-sl-backtest", label: "TP/SL backtest" },
  { href: "/bitcoin-backtest", label: "Bitcoin backtest" },
  { href: "/crypto-strategy-tester", label: "Crypto strategy tester" },
] as const;
