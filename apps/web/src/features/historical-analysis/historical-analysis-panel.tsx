"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import { useAuth } from "../auth/auth-provider";
import { useMarkets } from "../markets/use-markets";
import { getSignalPresets } from "../signals/api";
import {
  isSignalAuthenticationError,
  signalErrorMessage,
} from "../signals/errors";
import type { SignalPreset } from "../signals/types";
import { AnalysisForm } from "./analysis-form";
import { formatTimeframe, formatUtcDateTime } from "./format";
import { ReportSummary } from "./report-summary";
import { RunList } from "./run-list";
import { RunStatus } from "./run-status";
import { useHistoricalAnalyses } from "./use-historical-analyses";

type AnalysisStep = "configure" | "processing" | "results";

const steps: Array<{ label: string; value: AnalysisStep }> = [
  { label: "Configure", value: "configure" },
  { label: "Processing", value: "processing" },
  { label: "Results", value: "results" },
];

function getActiveStep(
  selectedRun: ReturnType<typeof useHistoricalAnalyses>["selectedRun"],
): AnalysisStep {
  if (!selectedRun) {
    return "configure";
  }
  return selectedRun.status === "succeeded" ? "results" : "processing";
}

function StepProgress({ activeStep }: { activeStep: AnalysisStep }) {
  return (
    <ol
      aria-label="Historical analysis progress"
      className="grid gap-2 sm:grid-cols-3"
    >
      {steps.map((step, index) => {
        const isCurrent = step.value === activeStep;
        const stepIndex = steps.findIndex((item) => item.value === activeStep);
        const isComplete = index < stepIndex;

        return (
          <li
            aria-current={isCurrent ? "step" : undefined}
            className={`rounded-xl border p-3 ${
              isCurrent
                ? "border-primary bg-primary/5"
                : isComplete
                  ? "border-success/50 bg-success/5"
                  : "bg-muted/30"
            }`}
            key={step.value}
          >
            <div className="flex items-center gap-3">
              <span
                aria-hidden="true"
                className="flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold"
              >
                {index + 1}
              </span>
              <span className="font-medium">{step.label}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function HistoricalAnalysisPanel() {
  const { csrfToken, refreshSession, status } = useAuth();
  const markets = useMarkets(status);
  const analysis = useHistoricalAnalyses({
    authStatus: status,
    csrfToken,
    refreshSession,
  });
  const [isPresetsLoading, setIsPresetsLoading] = useState(false);
  const [presetError, setPresetError] = useState<string | null>(null);
  const [presets, setPresets] = useState<SignalPreset[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isConfirmingCancellation, setIsConfirmingCancellation] = useState(false);
  const [isRunsSheetOpen, setIsRunsSheetOpen] = useState(false);
  const selectedRunHeadingRef = useRef<HTMLHeadingElement>(null);
  const focusStatusAfterCreateRef = useRef(false);

  const refreshPresets = useCallback(async () => {
    if (status !== "authenticated") {
      return;
    }

    setIsPresetsLoading(true);
    setPresetError(null);
    try {
      const response = await getSignalPresets();
      setPresets(response.presets);
    } catch (requestError) {
      if (isSignalAuthenticationError(requestError)) {
        await refreshSession();
      }
      setPresets([]);
      setPresetError(signalErrorMessage(requestError));
    } finally {
      setIsPresetsLoading(false);
    }
  }, [refreshSession, status]);

  useEffect(() => {
    if (status !== "authenticated") {
      setPresets([]);
      setPresetError(null);
      setIsPresetsLoading(false);
      return;
    }

    void refreshPresets();
  }, [refreshPresets, status]);

  useEffect(() => {
    setIsConfirmingCancellation(false);
  }, [analysis.selectedRunId]);

  useEffect(() => {
    if (!analysis.selectedRunId) {
      return;
    }

    window.requestAnimationFrame(() => {
      if (focusStatusAfterCreateRef.current) {
        document
          .getElementById("historical-analysis-run-status-heading")
          ?.focus();
        focusStatusAfterCreateRef.current = false;
        return;
      }
      selectedRunHeadingRef.current?.focus();
    });
  }, [analysis.selectedRunId]);

  async function handleCreate(
    request: Parameters<typeof analysis.createRun>[0],
    idempotencyKey: string,
  ) {
    setIsSubmitting(true);
    focusStatusAfterCreateRef.current = true;
    try {
      const run = await analysis.createRun(request, idempotencyKey);
      toast.success("Historical analysis queued.");
      return run;
    } catch (error) {
      focusStatusAfterCreateRef.current = false;
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSelectRun(runId: string) {
    focusStatusAfterCreateRef.current = false;
    setIsRunsSheetOpen(false);
    analysis.selectRun(runId);
  }

  async function handleCancel() {
    const cancelled = await analysis.cancelRun();
    if (cancelled) {
      setIsConfirmingCancellation(false);
    }
  }

  if (status !== "authenticated") {
    return null;
  }

  const currentConfiguration = analysis.configuration;
  const selectedRun = analysis.selectedRun;
  const configurationUnavailable =
    !currentConfiguration && !analysis.isConfigurationLoading;
  const marketUnavailable =
    !markets.isLoading &&
    !markets.error &&
    !markets.markets.some(
      (market) =>
        market.status === "available" &&
        market.baseAsset !== null &&
        market.quoteAsset !== null,
    );
  const presetUnavailable =
    !isPresetsLoading &&
    !presetError &&
    !presets.some((preset) => preset.status === "available");
  const selectedRunCanCancel =
    selectedRun?.status === "queued" || selectedRun?.status === "running";
  const activeStep = getActiveStep(selectedRun);

  return (
    <div className="space-y-6">
      <Alert className="border-warning/50 bg-warning/10" variant="warning">
        <AlertTitle>Historical hypothetical simulation</AlertTitle>
        <AlertDescription>
          Historical analysis is not financial advice, not a prediction, and no
          guarantee. It does not create live signals, alerts, Telegram messages,
          provider requests, or trading actions.
        </AlertDescription>
      </Alert>

      <StepProgress activeStep={activeStep} />

      <div className="xl:hidden">
        <Button
          onClick={() => setIsRunsSheetOpen(true)}
          type="button"
          variant="outline"
        >
          View previous analyses
        </Button>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-6">
          <section aria-labelledby="historical-analysis-configure-heading">
            <Card>
              <CardHeader>
                <CardTitle id="historical-analysis-configure-heading">
                  Configure analysis
                </CardTitle>
                <CardDescription>
                  Use a fixed server-controlled preset over a bounded UTC range
                  of stored historical candles.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {analysis.isConfigurationLoading ? (
                  <p aria-live="polite">Loading server-controlled analysis settings…</p>
                ) : null}
                {analysis.configurationError ? (
                  <InlineError
                    message={analysis.configurationError}
                    retryAction={
                      <InlineErrorRetryButton
                        onRetry={() => void analysis.refreshConfiguration()}
                      />
                    }
                    title="Analysis settings unavailable"
                  />
                ) : null}
                {currentConfiguration && !analysis.isConfigurationLoading ? (
                  <>
                    {markets.isLoading ? (
                      <p aria-live="polite">Loading supported markets…</p>
                    ) : null}
                    {markets.error ? (
                      <InlineError
                        message={markets.error}
                        retryAction={
                          <InlineErrorRetryButton
                            onRetry={() => void markets.refreshMarkets()}
                          />
                        }
                        title="Supported markets unavailable"
                      />
                    ) : null}
                    {presetError ? (
                      <InlineError
                        message={presetError}
                        retryAction={
                          <InlineErrorRetryButton
                            onRetry={() => void refreshPresets()}
                          />
                        }
                        title="Fixed presets unavailable"
                      />
                    ) : null}
                    {isPresetsLoading ? (
                      <p aria-live="polite">Loading fixed preset versions…</p>
                    ) : null}
                    {!markets.error && !markets.isLoading && marketUnavailable ? (
                      <Alert>
                        <AlertTitle>No supported market is ready</AlertTitle>
                        <AlertDescription>
                          Historical analysis is temporarily unavailable until a
                          supported market is ready.
                        </AlertDescription>
                      </Alert>
                    ) : null}
                    {!presetError && !isPresetsLoading && presetUnavailable ? (
                      <Alert>
                        <AlertTitle>No fixed preset is available</AlertTitle>
                        <AlertDescription>
                          Historical analysis is temporarily unavailable until a
                          fixed preset is available.
                        </AlertDescription>
                      </Alert>
                    ) : null}
                    {!markets.error &&
                    !markets.isLoading &&
                    !marketUnavailable &&
                    !presetError &&
                    !isPresetsLoading &&
                    !presetUnavailable ? (
                      <AnalysisForm
                        configuration={currentConfiguration}
                        isSubmitting={isSubmitting}
                        markets={markets.markets}
                        onSubmit={handleCreate}
                        presets={presets}
                      />
                    ) : null}
                  </>
                ) : null}
                {configurationUnavailable && !analysis.configurationError ? (
                  <Alert>
                    <AlertTitle>Analysis settings unavailable</AlertTitle>
                    <AlertDescription>
                      Historical-analysis settings are temporarily unavailable.
                    </AlertDescription>
                  </Alert>
                ) : null}
              </CardContent>
            </Card>
          </section>

          {analysis.error ? (
            <InlineError
              message={analysis.error}
              retryAction={<InlineErrorRetryButton onRetry={() => void analysis.refreshRuns()} />}
              title="Historical analysis request failed"
            />
          ) : null}

          {analysis.announcement ? (
            <p aria-live="polite" className="sr-only">
              {analysis.announcement}
            </p>
          ) : null}

          {selectedRun ? (
            <section
              aria-labelledby="historical-analysis-selected-heading"
              className="space-y-5"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <h2
                    className="text-xl font-semibold outline-none"
                    id="historical-analysis-selected-heading"
                    ref={selectedRunHeadingRef}
                    tabIndex={-1}
                  >
                    Selected analysis
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {selectedRun.market.symbol} · {selectedRun.preset.name} ·{" "}
                    {formatTimeframe(selectedRun.preset.timeframe)} ·{" "}
                    {formatUtcDateTime(selectedRun.analysisStart)} →{" "}
                    {formatUtcDateTime(selectedRun.analysisEnd)}
                  </p>
                </div>
                {selectedRunCanCancel ? (
                  <>
                    <Button
                      disabled={analysis.isCancelling}
                      onClick={() => setIsConfirmingCancellation(true)}
                      type="button"
                      variant="destructive"
                    >
                      Cancel analysis
                    </Button>
                    <ConfirmActionDialog
                      confirmLabel="Confirm cancellation"
                      description="A running analysis will stop at its next safe checkpoint. A queued analysis will be cancelled without creating a report."
                      isPending={analysis.isCancelling}
                      onConfirm={() => void handleCancel()}
                      onOpenChange={(open) => {
                        if (!open && !analysis.isCancelling) {
                          setIsConfirmingCancellation(false);
                        }
                      }}
                      open={isConfirmingCancellation}
                      title="Cancel this historical analysis?"
                    />
                  </>
                ) : null}
              </div>

              <RunStatus run={selectedRun} />

              {selectedRun.status === "failed" || selectedRun.status === "cancelled" ? (
                <Button
                  onClick={() => analysis.clearSelectedRun()}
                  type="button"
                  variant="outline"
                >
                  Create another analysis
                </Button>
              ) : null}

              <ReportSummary
                equity={analysis.equity}
                equityError={analysis.equityError}
                equityNextCursor={analysis.equityNextCursor}
                hasLoadedEquity={analysis.hasLoadedEquity}
                hasLoadedTrades={analysis.hasLoadedTrades}
                isEquityLoading={analysis.isEquityLoading}
                isReportLoading={analysis.isReportLoading}
                isTradesLoading={analysis.isTradesLoading}
                onLoadEquity={() => void analysis.loadEquity()}
                onLoadTrades={() => void analysis.loadMoreTrades()}
                report={analysis.report}
                reportError={analysis.reportError}
                selectedRun={selectedRun}
                trades={analysis.trades}
                tradesError={analysis.tradesError}
                tradesNextCursor={analysis.tradesNextCursor}
              />
            </section>
          ) : null}
        </div>

        <aside className="hidden min-w-0 xl:block">
          <Card className="sticky top-20">
            <CardContent className="p-4">
              <RunList
                headingId="historical-analysis-runs-heading-desktop"
                isLoading={analysis.isRunsLoading}
                isLoadingMore={analysis.isLoadingMoreRuns}
                nextCursor={analysis.runsNextCursor}
                onLoadMore={() => void analysis.loadMoreRuns()}
                onSelect={handleSelectRun}
                runs={analysis.runs}
                selectedRunId={analysis.selectedRunId}
              />
            </CardContent>
          </Card>
        </aside>
      </div>

      <Sheet onOpenChange={setIsRunsSheetOpen} open={isRunsSheetOpen}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-md" side="right">
          <SheetHeader>
            <SheetTitle>Previous analyses</SheetTitle>
            <SheetDescription>
              Select a run to close this panel and inspect it in the main workflow.
            </SheetDescription>
          </SheetHeader>
          <div className="overflow-y-auto px-4 pb-6">
            <RunList
              headingId="historical-analysis-runs-heading-mobile"
              isLoading={analysis.isRunsLoading}
              isLoadingMore={analysis.isLoadingMoreRuns}
              nextCursor={analysis.runsNextCursor}
              onLoadMore={() => void analysis.loadMoreRuns()}
              onSelect={handleSelectRun}
              runs={analysis.runs}
              selectedRunId={analysis.selectedRunId}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
