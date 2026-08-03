"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "../auth/auth-provider";
import { useMarkets } from "../markets/use-markets";
import { getSignalPresets } from "../signals/api";
import {
  isSignalAuthenticationError,
  signalErrorMessage,
} from "../signals/errors";
import type { SignalPreset } from "../signals/types";
import { AnalysisForm } from "./analysis-form";
import { historicalAnalysisFailureMessage } from "./errors";
import { formatUtcDateTime } from "./format";
import { ReportSummary } from "./report-summary";
import { RunList } from "./run-list";
import { RunStatus } from "./run-status";
import { useHistoricalAnalyses } from "./use-historical-analyses";

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

  async function handleCreate(
    request: Parameters<typeof analysis.createRun>[0],
    idempotencyKey: string,
  ) {
    setIsSubmitting(true);
    try {
      return await analysis.createRun(request, idempotencyKey);
    } finally {
      setIsSubmitting(false);
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

  return (
    <section
      aria-labelledby="historical-analysis-heading"
      className="space-y-6 rounded-xl border border-zinc-200 p-5 dark:border-zinc-700"
    >
      <div className="space-y-2">
        <h2 className="text-xl font-semibold" id="historical-analysis-heading">
          Historical analysis
        </h2>
        <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          Analyze how a fixed preset behaved over stored historical candles using
          one server-controlled hypothetical simulation. Historical results are
          not predictions or financial advice.
        </p>
      </div>

      <div aria-live="polite" className="space-y-2">
        {analysis.announcement ? <p>{analysis.announcement}</p> : null}
        {analysis.error ? (
          <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">
            {analysis.error}
          </p>
        ) : null}
      </div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Create an analysis</h3>
        {analysis.isConfigurationLoading ? (
          <p aria-live="polite">Loading server-controlled analysis settings…</p>
        ) : null}
        {analysis.configurationError ? (
          <div className="space-y-2">
            <p className="text-sm text-red-700 dark:text-red-300">
              {analysis.configurationError}
            </p>
            <button
              className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700"
              onClick={() => void analysis.refreshConfiguration()}
              type="button"
            >
              Retry analysis settings
            </button>
          </div>
        ) : null}
        {currentConfiguration && !analysis.isConfigurationLoading ? (
          <>
            {markets.isLoading ? (
              <p aria-live="polite">Loading supported markets…</p>
            ) : null}
            {markets.error ? (
              <div className="space-y-2">
                <p>{markets.error}</p>
                <button
                  className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700"
                  onClick={() => void markets.refreshMarkets()}
                  type="button"
                >
                  Retry markets
                </button>
              </div>
            ) : null}
            {presetError ? (
              <div className="space-y-2">
                <p>{presetError}</p>
                <button
                  className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700"
                  onClick={() => void refreshPresets()}
                  type="button"
                >
                  Retry presets
                </button>
              </div>
            ) : null}
            {isPresetsLoading ? (
              <p aria-live="polite">Loading fixed preset versions…</p>
            ) : null}
            {!markets.error && !markets.isLoading && marketUnavailable ? (
              <p>Historical analysis is temporarily unavailable because no supported market is ready.</p>
            ) : null}
            {!presetError && !isPresetsLoading && presetUnavailable ? (
              <p>Historical analysis is temporarily unavailable because no fixed preset is available.</p>
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
          <p>Historical-analysis settings are temporarily unavailable.</p>
        ) : null}
      </div>

      <RunList
        isLoading={analysis.isRunsLoading}
        isLoadingMore={analysis.isLoadingMoreRuns}
        nextCursor={analysis.runsNextCursor}
        onLoadMore={() => void analysis.loadMoreRuns()}
        onSelect={analysis.selectRun}
        runs={analysis.runs}
        selectedRunId={analysis.selectedRunId}
      />

      {selectedRun ? (
        <section
          aria-labelledby="historical-analysis-selected-heading"
          className="space-y-5 border-t border-zinc-200 pt-5 dark:border-zinc-700"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold" id="historical-analysis-selected-heading">
                Selected analysis
              </h3>
              <p className="text-sm text-zinc-600 dark:text-zinc-300">
                {selectedRun.market.symbol} · {selectedRun.preset.name} ·{" "}
                {formatUtcDateTime(selectedRun.analysisStart)} →{" "}
                {formatUtcDateTime(selectedRun.analysisEnd)}
              </p>
            </div>
            {selectedRunCanCancel ? (
              <div className="space-y-2">
                {!isConfirmingCancellation ? (
                  <button
                    className="rounded-lg border border-red-300 px-4 py-2 font-medium text-red-800 dark:border-red-900 dark:text-red-300"
                    disabled={analysis.isCancelling}
                    onClick={() => setIsConfirmingCancellation(true)}
                    type="button"
                  >
                    Cancel analysis
                  </button>
                ) : (
                  <div className="space-y-2 rounded-lg border border-red-300 p-3 dark:border-red-900">
                    <p className="text-sm">
                      Cancel this analysis? A running analysis will stop at its next safe checkpoint.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700"
                        disabled={analysis.isCancelling}
                        onClick={() => setIsConfirmingCancellation(false)}
                        type="button"
                      >
                        Keep analysis
                      </button>
                      <button
                        className="rounded-lg bg-red-700 px-3 py-2 font-medium text-white disabled:opacity-60"
                        disabled={analysis.isCancelling}
                        onClick={() => {
                          void analysis.cancelRun().then((cancelled) => {
                            if (cancelled) {
                              setIsConfirmingCancellation(false);
                            }
                          });
                        }}
                        type="button"
                      >
                        {analysis.isCancelling ? "Requesting cancellation…" : "Confirm cancellation"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>

          <RunStatus run={selectedRun} />
          {selectedRun.status === "failed" ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              {historicalAnalysisFailureMessage(selectedRun.failureCode)}
            </p>
          ) : null}
          {selectedRun.status === "cancelled" ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              No report was created for this cancelled analysis.
            </p>
          ) : null}
          <ReportSummary
            equity={analysis.equity}
            equityError={analysis.equityError}
            equityNextCursor={analysis.equityNextCursor}
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
    </section>
  );
}
