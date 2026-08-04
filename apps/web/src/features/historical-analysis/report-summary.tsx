"use client";

import { useEffect, useState } from "react";

import { InlineError } from "@/components/inline-error";
import { MetricCard } from "@/components/metric-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

import {
  formatAssumptionKey,
  formatAssumptionValue,
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
  HistoricalAnalysisEquityPoint,
  HistoricalAnalysisReport,
  HistoricalAnalysisRun,
  HistoricalAnalysisTrade,
} from "./types";
import { EquityChart } from "./equity-chart";
import { EquityTable } from "./equity-table";
import { TradeTable } from "./trade-table";

type ReportSummaryProps = {
  equity: HistoricalAnalysisEquityPoint[];
  equityError: string | null;
  equityNextCursor: string | null;
  hasLoadedEquity: boolean;
  hasLoadedTrades: boolean;
  isEquityLoading: boolean;
  isReportLoading: boolean;
  isTradesLoading: boolean;
  onLoadEquity: () => void;
  onLoadTrades: () => void;
  report: HistoricalAnalysisReport | null;
  reportError: string | null;
  selectedRun: HistoricalAnalysisRun | null;
  trades: HistoricalAnalysisTrade[];
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
    <details className="rounded-xl border p-4">
      <summary className="cursor-pointer font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
        {title}
      </summary>
      <dl className="mt-4 grid gap-x-4 gap-y-3 text-sm sm:grid-cols-2">
        {entries.map(([key, value]) => (
          <div key={key}>
            <dt className="font-medium">{formatAssumptionKey(key)}</dt>
            <dd className="break-words text-muted-foreground">
              {formatValue(key, value)}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function FingerprintDetail({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  const [isCopied, setIsCopied] = useState(false);

  async function copyFingerprint() {
    try {
      await navigator.clipboard.writeText(value);
      setIsCopied(true);
      window.setTimeout(() => setIsCopied(false), 2_000);
    } catch {
      setIsCopied(false);
    }
  }

  return (
    <div className="space-y-2">
      <dt className="font-medium">{label}</dt>
      <div className="flex flex-wrap items-center gap-2">
        <dd className="break-all text-muted-foreground">
          <span aria-hidden="true">{formatFingerprint(value)}</span>
          <span className="sr-only">{value}</span>
        </dd>
        <Button
          onClick={() => void copyFingerprint()}
          size="sm"
          type="button"
          variant="outline"
        >
          {isCopied ? "Copied" : "Copy fingerprint"}
        </Button>
      </div>
    </div>
  );
}

function signedMetric(value: string | null, undefinedReason?: string | null) {
  const formatted = formatSignedPercent(value, undefinedReason);
  const tone =
    value?.startsWith("-")
      ? "text-destructive"
      : value && value !== "0"
        ? "text-success"
        : undefined;

  return <span className={tone}>{formatted}</span>;
}

function ReportContext({ report }: { report: HistoricalAnalysisReport }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {report.preset.name} on {report.market.symbol}
        </CardTitle>
        <CardDescription>
          {formatUtcDateTime(report.analysisStart)} →{" "}
          {formatUtcDateTime(report.analysisEnd)} · {formatTimeframe(report.preset.timeframe)}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          label="Market"
          value={`${report.market.baseAsset}/${report.market.quoteAsset} (${report.market.symbol})`}
        />
        <MetricCard
          label="Preset code / version"
          value={`${report.preset.code} · v${report.preset.version}`}
        />
        <MetricCard
          label="Strategy type"
          value={formatStrategyType(report.preset.strategyType)}
        />
        <MetricCard label="Direction" value={formatDirection(report.preset.direction)} />
        <MetricCard label="Calculation version" value={report.calculationVersion} />
        <MetricCard label="Engine version" value={report.engineVersion} />
        <MetricCard label="Assumption version" value={report.assumptionVersion} />
        <MetricCard label="Dataset snapshot ID" value={report.datasetId} />
        <MetricCard label="Report ID" value={report.reportId} />
      </CardContent>
    </Card>
  );
}

function PrimaryMetrics({ report }: { report: HistoricalAnalysisReport }) {
  const { summary } = report;

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <MetricCard label="Net return" value={signedMetric(summary.netReturn)} />
      <MetricCard
        label="Maximum drawdown"
        value={signedMetric(summary.maximumDrawdown)}
      />
      <MetricCard
        label="Win rate"
        value={formatPercent(summary.winRate, summary.winRateUndefinedReason)}
      />
      <MetricCard
        label="Profit factor"
        value={
          summary.profitFactor === null
            ? formatUndefinedMetric(summary.profitFactorUndefinedReason)
            : summary.profitFactor
        }
      />
      <MetricCard label="Executed trades" value={summary.tradeCount} />
    </div>
  );
}

function SecondaryMetrics({ report }: { report: HistoricalAnalysisReport }) {
  const { summary } = report;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Additional report metrics</CardTitle>
        <CardDescription>
          Counts and server-provided values for the selected hypothetical run.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard label="Gross return" value={signedMetric(summary.grossReturn)} />
        <MetricCard label="Signal count" value={summary.signalCount} />
        <MetricCard label="Analysis candle count" value={summary.analysisCandleCount} />
        <MetricCard
          label="Wins / losses / flat"
          value={`${summary.winningTradeCount} / ${summary.losingTradeCount} / ${summary.flatTradeCount}`}
        />
        <MetricCard label="Initial equity" value={summary.initialEquity} />
        <MetricCard label="Final equity" value={summary.finalEquity} />
        <MetricCard
          label="Overlapping signals ignored"
          value={summary.overlappingSignalCount}
        />
        <MetricCard
          label="Incomplete-forward-window signals"
          value={summary.insufficientForwardSignalCount}
        />
        <MetricCard
          label="Equity-exhausted signals"
          value={summary.equityExhaustedSignalCount}
        />
      </CardContent>
    </Card>
  );
}

function Methodology({ report }: { report: HistoricalAnalysisReport }) {
  const coverageEntries = Object.entries(report.coverage).filter(
    ([key]) => key !== "manifestFingerprint",
  );
  const assumptionEntries = Object.entries(report.assumptions).filter(
    ([key]) => key !== "safety_disclosures" && key !== "safetyDisclosures",
  );

  return (
    <div className="space-y-4">
      <ReportContext report={report} />
      <Card>
        <CardHeader>
          <CardTitle>Data coverage and assumptions</CardTitle>
          <CardDescription>
            Full server snapshots remain available without changing their domain meaning.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
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
          <details className="rounded-xl border p-4">
            <summary className="cursor-pointer font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
              View dataset and result fingerprints
            </summary>
            <dl className="mt-4 space-y-3 text-sm">
              <FingerprintDetail
                label="Dataset fingerprint"
                value={report.datasetFingerprint}
              />
              <FingerprintDetail
                label="Result fingerprint"
                value={report.resultFingerprint}
              />
            </dl>
          </details>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Safety disclosures</CardTitle>
          <CardDescription>
            These statements describe the limits of this historical hypothetical simulation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
            {report.safetyDisclosures.map((disclosure, index) => (
              <li key={`${disclosure}-${index}`}>{disclosure}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

export function ReportSummary({
  equity,
  equityError,
  equityNextCursor,
  hasLoadedEquity,
  hasLoadedTrades,
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
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    setActiveTab("overview");
  }, [report?.reportId]);

  if (isReportLoading) {
    return <p aria-live="polite">Loading historical-analysis report…</p>;
  }
  if (reportError) {
    return <InlineError message={reportError} title="Historical report unavailable" />;
  }
  if (!report || !selectedRun || selectedRun.status !== "succeeded") {
    return null;
  }

  function handleTabChange(value: string) {
    setActiveTab(value);
    if (value === "trades" && report.tradesAvailable && !hasLoadedTrades) {
      onLoadTrades();
    }
    if (value === "equity" && report.equityAvailable && !hasLoadedEquity) {
      onLoadEquity();
    }
  }

  return (
    <section aria-labelledby="historical-analysis-report-heading" className="space-y-6">
      <Alert
        className="border-warning/50 bg-warning/10"
        variant="warning"
      >
        <AlertTitle id="historical-analysis-report-heading">
          Historical hypothetical simulation
        </AlertTitle>
        <AlertDescription>
          Not financial advice. This is not a prediction or guarantee. Real
          execution may differ. Synthetic-short results are not executable
          Binance Spot trades.
        </AlertDescription>
      </Alert>

      <Tabs onValueChange={handleTabChange} value={activeTab}>
        <TabsList aria-label="Historical analysis report sections" className="w-full flex-wrap justify-start sm:w-auto" variant="line">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trades">Hypothetical trades</TabsTrigger>
          <TabsTrigger value="equity">Equity data</TabsTrigger>
          <TabsTrigger value="methodology">Methodology</TabsTrigger>
        </TabsList>

        <TabsContent className="space-y-6" forceMount value="overview">
          <ReportContext report={report} />
          <PrimaryMetrics report={report} />
          <SecondaryMetrics report={report} />
          <Card>
            <CardHeader>
              <CardTitle>Equity progression</CardTitle>
              <CardDescription>
                The chart uses only the server-provided at-most-200-point preview.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EquityChart points={report.equityPreview} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent className="space-y-4" forceMount value="trades">
          <Card>
            <CardHeader>
              <CardTitle>Hypothetical trades</CardTitle>
              <CardDescription>
                Immutable trades from the selected historical simulation. No
                live execution is implied.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {report.tradesAvailable ? (
                <TradeTable
                  error={tradesError}
                  isLoading={isTradesLoading}
                  nextCursor={tradesNextCursor}
                  onLoadMore={onLoadTrades}
                  trades={trades}
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  Detailed hypothetical trades are not available for this report.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent className="space-y-4" forceMount value="equity">
          <Card>
            <CardHeader>
              <CardTitle>Equity data</CardTitle>
              <CardDescription>
                Immutable equity points retain exact server strings, candle
                identity, drawdown, and position state.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {report.equityAvailable ? (
                <EquityTable
                  error={equityError}
                  isLoading={isEquityLoading}
                  nextCursor={equityNextCursor}
                  onLoadMore={onLoadEquity}
                  points={equity}
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  Detailed equity data is not available for this report.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent className="space-y-4" forceMount value="methodology">
          <Methodology report={report} />
        </TabsContent>
      </Tabs>
    </section>
  );
}
