export type HistoricalScenarioName =
  | "analysis-positive"
  | "analysis-negative"
  | "analysis-zero-trade"
  | "analysis-paginated"
  | "analysis-missing-coverage";

type HistoricalScenarioManifest = {
  scenario: HistoricalScenarioName;
  symbol: string;
  presetCode: string;
  presetVersion: number;
  analysisStart: string;
  analysisEnd: string;
  expected: {
    initialEquity: string;
    netReturn: "positive" | "negative" | "zero";
    maximumDrawdown: "positive" | "zero";
    tradeCount: { minimum: number; exact?: number };
    winningTradeCount: { minimum: number; exact?: number };
    losingTradeCount: { minimum: number; exact?: number };
    winRate: "defined" | "undefined";
    profitFactor: "defined" | "undefined";
    undefinedReason?: string;
  };
};

export const HISTORICAL_SCENARIOS: Record<
  HistoricalScenarioName,
  HistoricalScenarioManifest
> = {
  "analysis-positive": {
    scenario: "analysis-positive",
    symbol: "ETHUSDT",
    presetCode: "price_sma_200_cross_above_1h",
    presetVersion: 1,
    analysisStart: "2026-07-20T00:00:00Z",
    analysisEnd: "2026-08-03T00:00:00Z",
    expected: {
      initialEquity: "10000",
      netReturn: "positive",
      maximumDrawdown: "positive",
      tradeCount: { minimum: 2 },
      winningTradeCount: { minimum: 1 },
      losingTradeCount: { minimum: 1 },
      winRate: "defined",
      profitFactor: "defined",
    },
  },
  "analysis-negative": {
    scenario: "analysis-negative",
    symbol: "SOLUSDT",
    presetCode: "price_sma_200_cross_above_1h",
    presetVersion: 1,
    analysisStart: "2026-07-20T00:00:00Z",
    analysisEnd: "2026-08-03T00:00:00Z",
    expected: {
      initialEquity: "10000",
      netReturn: "negative",
      maximumDrawdown: "positive",
      tradeCount: { minimum: 2 },
      winningTradeCount: { minimum: 0 },
      losingTradeCount: { minimum: 1 },
      winRate: "defined",
      profitFactor: "defined",
    },
  },
  "analysis-zero-trade": {
    scenario: "analysis-zero-trade",
    symbol: "XRPUSDT",
    presetCode: "price_sma_200_cross_below_4h",
    presetVersion: 1,
    analysisStart: "2026-07-20T00:00:00Z",
    analysisEnd: "2026-08-03T00:00:00Z",
    expected: {
      initialEquity: "10000",
      netReturn: "zero",
      maximumDrawdown: "zero",
      tradeCount: { minimum: 0, exact: 0 },
      winningTradeCount: { minimum: 0, exact: 0 },
      losingTradeCount: { minimum: 0, exact: 0 },
      winRate: "undefined",
      profitFactor: "undefined",
      undefinedReason: "no_trades",
    },
  },
  "analysis-paginated": {
    scenario: "analysis-paginated",
    symbol: "BNBUSDT",
    presetCode: "price_sma_200_cross_above_1h",
    presetVersion: 1,
    analysisStart: "2026-05-05T00:00:00Z",
    analysisEnd: "2026-08-03T00:00:00Z",
    expected: {
      initialEquity: "10000",
      netReturn: "positive",
      maximumDrawdown: "zero",
      tradeCount: { minimum: 55 },
      winningTradeCount: { minimum: 55 },
      losingTradeCount: { minimum: 0 },
      winRate: "defined",
      profitFactor: "defined",
    },
  },
  "analysis-missing-coverage": {
    scenario: "analysis-missing-coverage",
    symbol: "BTCUSDT",
    presetCode: "price_sma_200_cross_above_1h",
    presetVersion: 1,
    analysisStart: "2026-07-20T00:00:00Z",
    analysisEnd: "2026-08-03T00:00:00Z",
    expected: {
      initialEquity: "10000",
      netReturn: "zero",
      maximumDrawdown: "zero",
      tradeCount: { minimum: 0, exact: 0 },
      winningTradeCount: { minimum: 0, exact: 0 },
      losingTradeCount: { minimum: 0, exact: 0 },
      winRate: "undefined",
      profitFactor: "undefined",
      undefinedReason: "report_unavailable",
    },
  },
};
