"use client";

import { useEffect, useState } from "react";

import {
  formatAssumptionKey,
  formatAssumptionValue,
  formatDecimal,
  formatDirection,
  formatFingerprint,
  formatPercent,
  formatSignedPercent,
  formatStrategyType,
  formatTimeframe,
  formatUndefinedMetric,
  formatUtcDateTime,
} from "./format";
import type {
  HistoricalAnalysisReport,
  HistoricalAnalysisRun,
} from "./types";
import { EquityChart } from "./equity-chart";
import { EquityTable } from "./equity-table";
import { TradeTable } from "./trade-table";

type ReportSummaryProps = {
  equity: import("./types").HistoricalAnalysisEquityPoint[];
  equityError: string | null;
  equityNextCursor: string | null;
  isEquityLoading: boolean;
  isReportLoading: boolean;
  isTradesLoading: boolean;
  onLoadEquity: () => void;
  onLoadTrades: () => void;
  report: HistoricalAnalysisReport | null;
  reportError: string | null;
  selectedRun: HistoricalAnalysisRun | null;
  trades: import("./types").HistoricalAnalysisTrade[];
  tradesError: string | null;
  tradesNextCursor: string | null;
};

function snapshotValue(_key: string, value: unknown): string {
  if (typeof value === "string") {
    if (value === "NaN" || value === "Infinity" || value === "-Infinity") {
      return "Not available";
    }
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "Not available";
}

function formatCoverageValue(key: string, value: unknown): string {
  if (typeof value === "string") {
    const normalizedKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
    if (
      value.includes("T") &&
      /(?:_time|_at|^time|^start|^end)/.test(normalizedKey)
    ) {
      return formatUtcDateTime(value);
    }
  }

  return snapshotValue(key, value);
}

function SnapshotDetails({
  entries,
  formatValue = snapshotValue,
  title,
}: {
  entries: Array<[string, unknown]>;
  formatValue?: (key: string, value: unknown) => string;
  title: string;
}) {
  return (
    <details className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
      <summary className="cursor-pointer font-medium">{title}</summary>
      <dl className="mt-3 grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2">
        {entries.map(([key, value]) => (
          <div key={key}>
            <dt className="font-medium">{formatAssumptionKey(key)}</dt>
            <dd className="break-words text-zinc-600 dark:text-zinc-300">
              {formatValue(key, value)}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-700">
      <dt className="text-sm text-zinc-600 dark:text-zinc-300">{label}</dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}

export function ReportSummary({
  equity,
  equityError,
  equityNextCursor,
  isEquityLoading,
  isReportLoading,
  isTradesLoading,
  onLoadEquity,
  onLoadTrades,
  report,
  reportError,
  selectedRun,
  trades,
  tradesError,
  tradesNextCursor,
}: ReportSummaryProps) {
  const [showDetailedEquity, setShowDetailedEquity] = useState(false);
  const [showTrades, setShowTrades] = useState(false);

  useEffect(() => {
    setShowDetailedEquity(false);
    setShowTrades(false);
  }, [report?.reportId]);

  if (isReportLoading) {
    return <p aria-live="polite">Loading historical-analysis report…</p>;
  }
  if (reportError) {
    return (
      <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">
        {reportError}
      </p>
    );
  }
  if (!report || !selectedRun || selectedRun.status !== "succeeded") {
    return null;
  }

  const { summary } = report;
  const coverageEntries = Object.entries(report.coverage).filter(
    ([key]) => key !== "manifestFingerprint",
  );
  const assumptionEntries = Object.entries(report.assumptions).filter(
    ([key]) => key !== "safety_disclosures" && key !== "safetyDisclosures",
  );

  return (
    <section aria-labelledby="historical-analysis-report-heading" className="space-y-6">
      <div className="space-y-3 rounded-lg border-2 border-zinc-900 p-4 dark:border-zinc-100">
        <p className="text-sm font-semibold tracking-wide uppercase">
          Historical hypothetical simulation
        </p>
        <h3 className="text-xl font-semibold" id="historical-analysis-report-heading">
          {report.preset.name} on {report.market.symbol}
        </h3>
        <p className="leading-6 text-zinc-600 dark:text-zinc-300">
          This is a historical hypothetical simulation using stored candle data
          and fixed assumptions. It is not financial advice, a prediction, or a
          guarantee of future results. Real execution, liquidity, fees, slippage,
          and market behavior may differ.
        </p>
        <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          Cross-below trades are shown as synthetic short analytical inverse
          exposure. They are not executable Binance Spot trades and do not model
          borrowing, margin, leverage, liquidation, or derivatives.
        </p>
        {report.safetyDisclosures.length ? (
          <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-600 dark:text-zinc-300">
            {report.safetyDisclosures.map((disclosure) => (
              <li key={disclosure}>{disclosure}</li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="Market" value={`${report.market.baseAsset}/${report.market.quoteAsset} (${report.market.symbol})`} />
        <Metric label="Preset code / version" value={`${report.preset.code} · v${report.preset.version}`} />
        <Metric label="Strategy type" value={formatStrategyType(report.preset.strategyType)} />
        <Metric label="Timeframe" value={formatTimeframe(report.preset.timeframe)} />
        <Metric label="Direction" value={formatDirection(report.preset.direction)} />
        <Metric label="Calculation version" value={report.calculationVersion} />
        <Metric label="Engine version" value={report.engineVersion} />
        <Metric label="Assumption version" value={report.assumptionVersion} />
        <Metric label="Dataset snapshot ID" value={report.datasetId} />
        <Metric label="Report ID" value={report.reportId} />
        <Metric
          label="UTC analysis range"
          value={`${formatUtcDateTime(report.analysisStart)} → ${formatUtcDateTime(report.analysisEnd)}`}
        />
      </div>

      <div className="space-y-3">
        <h4 className="text-lg font-semibold">Data coverage and assumptions</h4>
        <SnapshotDetails
          entries={coverageEntries}
          formatValue={formatCoverageValue}
          title="View stored data coverage"
        />
        <SnapshotDetails
          entries={assumptionEntries}
          formatValue={formatAssumptionValue}
          title="View complete execution assumptions"
        />
        <details className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-700">
          <summary className="cursor-pointer font-medium">
            View dataset and result fingerprints
          </summary>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="font-medium">Dataset fingerprint</dt>
              <dd className="break-all text-zinc-600 dark:text-zinc-300">
                <span aria-hidden="true">{formatFingerprint(report.datasetFingerprint)}</span>
                <span className="sr-only">{report.datasetFingerprint}</span>
              </dd>
            </div>
            <div>
              <dt className="font-medium">Result fingerprint</dt>
              <dd className="break-all text-zinc-600 dark:text-zinc-300">
                <span aria-hidden="true">{formatFingerprint(report.resultFingerprint)}</span>
                <span className="sr-only">{report.resultFingerprint}</span>
              </dd>
            </div>
          </dl>
        </details>
      </div>

      <div className="space-y-3">
        <h4 className="text-lg font-semibold">Summary metrics</h4>
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric label="Analysis candles" value={summary.analysisCandleCount} />
          <Metric label="Signals" value={summary.signalCount} />
          <Metric label="Executed trades" value={summary.tradeCount} />
          <Metric
            label="Wins / losses / flat"
            value={`${summary.winningTradeCount} / ${summary.losingTradeCount} / ${summary.flatTradeCount}`}
          />
          <Metric label="Gross return" value={formatSignedPercent(summary.grossReturn)} />
          <Metric label="Net return" value={formatSignedPercent(summary.netReturn)} />
          <Metric
            label="Maximum drawdown"
            value={formatSignedPercent(summary.maximumDrawdown)}
          />
          <Metric
            label="Win rate"
            value={formatPercent(summary.winRate, summary.winRateUndefinedReason)}
          />
          <Metric
            label="Profit factor"
            value={
              summary.profitFactor === null
                ? historicalAnalysisUndefinedMetric(summary.profitFactorUndefinedReason)
                : formatDecimal(summary.profitFactor)
            }
          />
          <Metric label="Initial equity" value={formatDecimal(summary.initialEquity)} />
          <Metric label="Final equity" value={formatDecimal(summary.finalEquity)} />
          <Metric label="Overlapping signals ignored" value={summary.overlappingSignalCount} />
          <Metric
            label="Signals without complete forward window"
            value={summary.insufficientForwardSignalCount}
          />
          <Metric
            label="Signals skipped after equity exhaustion"
            value={summary.equityExhaustedSignalCount}
          />
        </dl>
      </div>

      <div className="space-y-3">
        <h4 className="text-lg font-semibold">Equity progression</h4>
        <EquityChart points={report.equityPreview} />
        {report.equityAvailable ? (
          <div className="space-y-3">
            <button
              className="rounded-lg border border-zinc-300 px-4 py-2 font-medium dark:border-zinc-700"
              onClick={() => {
                setShowDetailedEquity((current) => !current);
                if (!showDetailedEquity && !equity.length) {
                  onLoadEquity();
                }
              }}
              type="button"
            >
              {showDetailedEquity
                ? "Hide detailed equity data"
                : "View detailed equity data"}
            </button>
            {showDetailedEquity ? (
              <EquityTable
                error={equityError}
                isLoading={isEquityLoading}
                nextCursor={equityNextCursor}
                onLoadMore={onLoadEquity}
                points={equity}
              />
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="space-y-3">
        <h4 className="text-lg font-semibold">Hypothetical trades</h4>
        {report.tradesAvailable ? (
          <>
            <button
              className="rounded-lg border border-zinc-300 px-4 py-2 font-medium dark:border-zinc-700"
              onClick={() => {
                setShowTrades((current) => !current);
                if (!showTrades && !trades.length) {
                  onLoadTrades();
                }
              }}
              type="button"
            >
              {showTrades ? "Hide hypothetical trades" : "View hypothetical trades"}
            </button>
            {showTrades ? (
              <TradeTable
                error={tradesError}
                isLoading={isTradesLoading}
                nextCursor={tradesNextCursor}
                onLoadMore={onLoadTrades}
                trades={trades}
              />
            ) : null}
          </>
        ) : (
          <p className="text-sm text-zinc-600 dark:text-zinc-300">
            Detailed hypothetical trades are not available for this report.
          </p>
        )}
      </div>
    </section>
  );
}

function historicalAnalysisUndefinedMetric(reason: string | null): string {
  return formatUndefinedMetric(reason);
}
