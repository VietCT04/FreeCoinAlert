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
  endOfRange: "incomplete_trade_not_opened";
};

export type HistoricalAnalysisConfiguration = {
  minimumRangeDays: number;
  maximumRangeDays: number;
  maximumActiveRuns: number;
  simulationVersion: string;
  assumptionVersion: string;
  assumptions: HistoricalAnalysisAssumptionsConfiguration;
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
};

export type HistoricalAnalysisReportSummary = {
  analysisCandleCount: number;
  signalCount: number;
  tradeCount: number;
  winningTradeCount: number;
  losingTradeCount: number;
  flatTradeCount: number;
  overlappingSignalCount: number;
  insufficientForwardSignalCount: number;
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

export type HistoricalAnalysisTrade = {
  sequence: number;
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
  exitCandleId: string;
  exitCandleRevision: number;
  exitCloseTime: string;
  exitRawPrice: string;
  exitFillPrice: string;
  holdingCandleCount: number;
  feeRate: string;
  slippageRate: string;
  equityBefore: string;
  grossReturn: string;
  netReturn: string;
  grossPnl: string;
  netPnl: string;
  equityAfter: string;
  outcome: string;
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
  resultFingerprint: string;
  datasetFingerprint: string;
  analysisStart: string;
  analysisEnd: string;
  coverage: Record<string, unknown>;
  assumptions: Record<string, unknown>;
  summary: HistoricalAnalysisReportSummary;
  safetyDisclosures: string[];
  equityPreview: HistoricalAnalysisEquityPoint[];
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
