export type PublicSeoRoute = Readonly<{
  path: string;
}>;

// Public acquisition and educational routes are intentionally bounded. Add a
// route only when its server-rendered page and metadata are implemented.
export const PUBLIC_SEO_ROUTES: readonly PublicSeoRoute[] = [
  { path: "/" },
  { path: "/crypto-backtesting" },
  { path: "/crypto-strategy-tester" },
  { path: "/bitcoin-backtest" },
  { path: "/rsi-backtest" },
  { path: "/sma-backtest" },
  { path: "/tp-sl-backtest" },
  { path: "/strategy-alerts" },
  { path: "/guides" },
  { path: "/guides/how-to-backtest-crypto-strategy" },
  { path: "/guides/rsi-backtesting" },
  { path: "/guides/rsi-cross-below-30-strategy" },
  { path: "/guides/sma-crossover-backtesting" },
  { path: "/guides/crypto-take-profit-stop-loss" },
  { path: "/guides/backtesting-vs-forward-testing" },
  { path: "/guides/backtesting-fees-slippage" },
  { path: "/guides/common-backtesting-mistakes" },
];

export const PRIVATE_NOINDEX_ROUTE_PREFIXES = [
  "/dashboard",
  "/price-alerts",
  "/preset-signals",
  "/historical-analysis",
  "/telegram",
  "/sign-in",
  "/sign-up",
] as const;

export function normalizeSeoRoutePath(path: string): string {
  if (
    !path.startsWith("/") ||
    path.startsWith("//") ||
    path.includes("?") ||
    path.includes("#")
  ) {
    throw new Error("SEO route paths must be path-only values.");
  }

  if (path.length > 1 && path.endsWith("/")) {
    return path.slice(0, -1);
  }

  return path;
}
