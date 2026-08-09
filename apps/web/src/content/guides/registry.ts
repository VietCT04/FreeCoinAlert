import type { GuideArticle } from "./types";
import { backtestingFeesSlippageGuide } from "./backtesting-fees-slippage";
import { backtestingVsForwardTestingGuide } from "./backtesting-vs-forward-testing";
import { commonBacktestingMistakesGuide } from "./common-backtesting-mistakes";
import { cryptoTakeProfitStopLossGuide } from "./crypto-take-profit-stop-loss";
import { howToBacktestCryptoStrategyGuide } from "./how-to-backtest-crypto-strategy";
import { rsiBacktestingGuide } from "./rsi-backtesting";
import { rsiCrossBelow30Guide } from "./rsi-cross-below-30-strategy";
import { smaCrossoverBacktestingGuide } from "./sma-crossover-backtesting";

export const GUIDES: readonly GuideArticle[] = [
  howToBacktestCryptoStrategyGuide,
  rsiBacktestingGuide,
  rsiCrossBelow30Guide,
  smaCrossoverBacktestingGuide,
  cryptoTakeProfitStopLossGuide,
  backtestingVsForwardTestingGuide,
  backtestingFeesSlippageGuide,
  commonBacktestingMistakesGuide,
];

const guideBySlug = new Map(GUIDES.map((guide) => [guide.slug, guide]));

export function getGuideBySlug(slug: string): GuideArticle | undefined {
  return guideBySlug.get(slug);
}
