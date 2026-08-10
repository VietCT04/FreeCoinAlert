/**
 * Immutable, non-live content for the public product preview.
 *
 * This fixture is intentionally separate from historical-analysis API data.
 * It is a stable server-safe contract for later homepage and social-preview
 * work; none of its values represent live prices or performance results.
 */
export const MARKETING_DEMO_STRATEGY = {
  symbol: "XRPUSDT",
  timeframe: "1H",
  entry: "RSI(14) crosses below 30",
  takeProfit: "+6%",
  stopLoss: "-3%",
  maxHolding: "7 candles",
} as const;

export const MARKETING_DEMO_CHART = {
  candles: [
    { x: 48, high: 58, open: 88, close: 72, low: 101, bullish: true },
    { x: 88, high: 66, open: 72, close: 92, low: 108, bullish: false },
    { x: 128, high: 76, open: 93, close: 82, low: 112, bullish: true },
    { x: 168, high: 70, open: 82, close: 61, low: 98, bullish: true },
    { x: 208, high: 54, open: 62, close: 80, low: 94, bullish: false },
    { x: 248, high: 72, open: 80, close: 106, low: 119, bullish: false },
    { x: 288, high: 96, open: 106, close: 124, low: 139, bullish: false },
    { x: 328, high: 114, open: 124, close: 108, low: 132, bullish: true },
    { x: 368, high: 98, open: 108, close: 86, low: 119, bullish: true },
    { x: 408, high: 78, open: 86, close: 96, low: 108, bullish: false },
    { x: 448, high: 82, open: 96, close: 74, low: 105, bullish: true },
    { x: 488, high: 62, open: 74, close: 82, low: 94, bullish: false },
    { x: 528, high: 70, open: 82, close: 58, low: 90, bullish: true },
  ],
  rsiPoints: [
    [48, 240],
    [88, 232],
    [128, 246],
    [168, 238],
    [208, 252],
    [248, 258],
    [288, 268],
    [328, 252],
    [368, 244],
    [408, 236],
    [448, 248],
    [488, 234],
    [528, 242],
  ],
  rsiThreshold: 250,
  entryCandleIndex: 6,
} as const;

export const MARKETING_DEMO_REPORT = {
  label: "Example historical simulation",
  status: "Entry detected",
  metrics: [
    { label: "Trades", value: "—" },
    { label: "Drawdown", value: "—" },
    { label: "Return", value: "—" },
  ],
} as const;

export type MarketingDemoStrategy = typeof MARKETING_DEMO_STRATEGY;
