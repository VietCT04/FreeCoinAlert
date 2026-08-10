import type { SignalPreset } from "../signals/types";

export type HistoricalAnalysisStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type HistoricalAnalysisAssumptionsConfiguration = {
  signalTiming: "confirmed_candle_close";
  entryTiming: "next_candle_open";
  holdingPeriodCandles: number;
  feeBpsPerSide: string;
  slippageBpsPerSide: string;
  positionSizing: "one_position_full_equity";
  overlappingSignals: "ignored";
  endOfRange:
    | "incomplete_trade_not_opened"
    | "open_at_end_mark_to_market";
};

export type HistoricalAnalysisExitRuleType =
  | "take_profit_percent"
  | "stop_loss_percent"
  | "rsi_threshold_cross"
  | "max_holding_candles";

export type HistoricalAnalysisStrategyExitRule = {
  type: HistoricalAnalysisExitRuleType;
  percent?: string;
  direction?: string;
  threshold?: string;
  period?: number;
  priceInput?: string;
  timeframe?: string;
  calculationVersion?: string;
  candles?: number;
};

export type HistoricalAnalysisStrategyRequest = {
  position_direction: "long";
  exit_rules: HistoricalAnalysisStrategyExitRule[];
};

export type HistoricalAnalysisStrategySnapshot = {
  version?: string;
  positionDirection: "long" | "synthetic_short";
  exitRules: HistoricalAnalysisStrategyExitRule[];
};

export type HistoricalAnalysisStrategy = {
  version: string;
  positionDirection: "long" | "synthetic_short";
  exitRules: HistoricalAnalysisStrategyExitRule[];
};

export type HistoricalAnalysisStrategyRuleCapability = {
  minimum?: string | number;
  maximum?: string | number;
  minimumInclusive?: boolean;
  maximumInclusive?: boolean;
  minimumExclusive?: string | number;
  maximumExclusive?: string | number;
  default?: string | number;
  directions?: string[];
  period?: number;
  priceInput?: string;
  timeframe?: string;
  calculationVersion?: string;
};

export type HistoricalAnalysisStrategyCapabilities = {
  configurableStrategyAvailable: boolean;
  positionDirections: string[];
  maximumExitRules: number;
  requiredExitRuleTypes: HistoricalAnalysisExitRuleType[];
  supportedExitRuleTypes?: HistoricalAnalysisExitRuleType[];
  sameCandlePriority: HistoricalAnalysisExitRuleType[];
  maxHoldingCandles: {
    minimum: number;
    maximum: number;
    default: number;
  };
  exitRuleLimits?: Partial<
    Record<HistoricalAnalysisExitRuleType, HistoricalAnalysisStrategyRuleCapability>
  >;
};

export type HistoricalAnalysisConfiguration = {
  minimumRangeDays: number;
  maximumRangeDays: number;
  maximumActiveRuns: number;
  simulationVersion: string;
  assumptionVersion: string;
  assumptions: HistoricalAnalysisAssumptionsConfiguration;
  strategyCapabilities?: HistoricalAnalysisStrategyCapabilities;
};

export type HistoricalAnalysisCoverageStatus =
  | "backfilling"
  | "ready"
  | "degraded"
  | "partial"
  | "unavailable";

export type HistoricalAnalysisCoverage = {
  market: {
    exchange: string;
    marketType: string;
    symbol: string;
  };
  preset: {
    code: string;
    version: number;
    timeframe: string;
  };
  status: HistoricalAnalysisCoverageStatus;
  firstAnalysisStart?: string | null;
  lastAnalysisEnd?: string | null;
  availableAnalysisDays: number;
  minimumRangeDays: number;
  maximumRangeDays: number;
  verifiedAt?: string | null;
  availableStart: string | null;
  availableEnd: string | null;
  targetStart: string;
  targetEnd: string;
  coveragePercent: number;
};

export type HistoricalAnalysisMarket = {
  exchange: string;
  marketType: string;
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
};

export type HistoricalAnalysisPreset = {
  code: string;
  version: number;
  name: string;
  strategyType: string;
  timeframe: string;
  direction: string;
  parameters: {
    period: number;
    threshold: string | null;
    priceInput: string;
  };
};

export type HistoricalAnalysisRun = {
  id: string;
  status: HistoricalAnalysisStatus;
  market: HistoricalAnalysisMarket;
  preset: HistoricalAnalysisPreset;
  calculationVersion: string;
  simulationVersion: string;
  assumptionVersion: string;
  strategyVersion: string;
  strategy: HistoricalAnalysisStrategy;
  strategyFingerprint: string;
  analysisStart: string;
  analysisEnd: string;
  progressStage: string;
  progressPercent: number;
  cancellationRequested: boolean;
  cancellationRequestedAt: string | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  failedAt: string | null;
  cancelledAt: string | null;
  failureCode: string | null;
};

export type HistoricalAnalysisRunEnvelope = {
  run: HistoricalAnalysisRun;
};

export type HistoricalAnalysisRunListEnvelope = {
  runs: HistoricalAnalysisRun[];
  nextCursor: string | null;
};

export type HistoricalAnalysisCreateRequest = {
  exchange: "binance";
  market_type: "spot";
  symbol: string;
  preset_code: string;
  preset_version: number;
  analysis_start: string;
  analysis_end: string;
  strategy?: HistoricalAnalysisStrategyRequest;
};

export type HistoricalAnalysisReportSummary = {
  analysisCandleCount: number;
  signalCount: number;
  tradeCount: number;
  closedTradeCount: number;
  openAtEndCount: number;
  winningTradeCount: number;
  losingTradeCount: number;
  flatTradeCount: number;
  overlappingSignalCount: number;
  insufficientForwardSignalCount: number;
  entryUnavailableSignalCount: number;
  equityExhaustedSignalCount: number;
  initialEquity: string;
  finalEquity: string;
  grossReturn: string;
  netReturn: string;
  maximumDrawdown: string;
  winRate: string | null;
  winRateUndefinedReason: string | null;
  profitFactor: string | null;
  profitFactorUndefinedReason: string | null;
  exitReasonCounts: Record<string, number>;
};

export type HistoricalAnalysisEquityPoint = {
  sequence: number;
  candleId: string;
  candleRevision: number;
  candleOpenTime: string;
  candleCloseTime: string;
  equity: string;
  drawdown: string;
  positionState: string;
  activeTradeSequence: number | null;
};

export type HistoricalAnalysisCandlePreview = {
  sequence: number;
  candleId: string;
  candleRevision: number;
  candleOpenTime: string;
  candleCloseTime: string;
  openPrice: string;
  highPrice: string;
  lowPrice: string;
  closePrice: string;
};

export type HistoricalAnalysisTradeMarker = {
  sequence: number;
  markerType: "entry" | "exit";
  side: "buy" | "sell";
  positionDirection: "long" | "synthetic_short";
  candleOpenTime: string;
  price: string;
  exitReason?: string | null;
  exitPriceBasis?: string | null;
  exitRule?: HistoricalAnalysisStrategyExitRule | null;
};

export type HistoricalAnalysisTrade = {
  sequence: number;
  tradeStatus: "closed" | "open_at_end";
  signalCandleId: string;
  signalCandleRevision: number;
  signalOpenTime: string;
  signalCloseTime: string;
  signalDirection: string;
  positionDirection: string;
  entryCandleId: string;
  entryCandleRevision: number;
  entryOpenTime: string;
  entryRawPrice: string;
  entryFillPrice: string;
  exitCandleId: string | null;
  exitCandleRevision: number | null;
  exitCloseTime: string | null;
  exitRawPrice: string | null;
  exitFillPrice: string | null;
  exitReason: string | null;
  exitPriceBasis: string | null;
  exitRule: HistoricalAnalysisStrategyExitRule | null;
  holdingCandleCount: number;
  feeRate: string;
  slippageRate: string;
  equityBefore: string;
  grossReturn: string;
  netReturn: string;
  grossPnl: string;
  netPnl: string;
  equityAfter: string;
  outcome: string | null;
  markCandleId: string | null;
  markCandleRevision: number | null;
  markCloseTime: string | null;
  markPrice: string | null;
  unrealizedReturn: string | null;
  unrealizedPnl: string | null;
};

export type HistoricalAnalysisReport = {
  reportId: string;
  runId: string;
  datasetId: string;
  market: HistoricalAnalysisMarket;
  preset: HistoricalAnalysisPreset;
  calculationVersion: string;
  engineVersion: string;
  assumptionVersion: string;
  strategy: HistoricalAnalysisStrategy;
  strategyFingerprint: string;
  resultFingerprint: string;
  datasetFingerprint: string;
  analysisStart: string;
  analysisEnd: string;
  coverage: Record<string, unknown>;
  assumptions: Record<string, unknown>;
  summary: HistoricalAnalysisReportSummary;
  safetyDisclosures: string[];
  equityPreview: HistoricalAnalysisEquityPoint[];
  candlePreview: HistoricalAnalysisCandlePreview[];
  tradeMarkers: HistoricalAnalysisTradeMarker[];
  tradesAvailable: boolean;
  equityAvailable: boolean;
  tradesPath: string;
  equityPath: string;
};

export type HistoricalAnalysisReportEnvelope = {
  report: HistoricalAnalysisReport;
};

export type HistoricalAnalysisTradesEnvelope = {
  trades: HistoricalAnalysisTrade[];
  nextCursor: string | null;
};

export type HistoricalAnalysisEquityEnvelope = {
  equity: HistoricalAnalysisEquityPoint[];
  nextCursor: string | null;
};

export type AvailableHistoricalPreset = SignalPreset;
