"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import {
  cancelHistoricalAnalysis,
  createHistoricalAnalysis,
  getHistoricalAnalysis,
  getHistoricalAnalysisConfiguration,
  getHistoricalAnalysisEquity,
  getHistoricalAnalysisReport,
  getHistoricalAnalyses,
  getHistoricalAnalysisTrades,
} from "./api";
import {
  historicalAnalysisErrorMessage,
  isHistoricalAnalysisAuthenticationError,
} from "./errors";
import type {
  HistoricalAnalysisConfiguration,
  HistoricalAnalysisCreateRequest,
  HistoricalAnalysisEquityPoint,
  HistoricalAnalysisReport,
  HistoricalAnalysisRun,
  HistoricalAnalysisTrade,
} from "./types";

type UseHistoricalAnalysesOptions = {
  authStatus: AuthStatus;
  csrfToken: string | null;
  refreshSession: () => Promise<void>;
};

export type HistoricalAnalysesState = {
  announcement: string | null;
  configuration: HistoricalAnalysisConfiguration | null;
  configurationError: string | null;
  error: string | null;
  equity: HistoricalAnalysisEquityPoint[];
  equityError: string | null;
  equityNextCursor: string | null;
  hasLoadedEquity: boolean;
  hasLoadedTrades: boolean;
  isConfigurationLoading: boolean;
  isCancelling: boolean;
  isEquityLoading: boolean;
  isLoadingMoreRuns: boolean;
  isReportLoading: boolean;
  isRunsLoading: boolean;
  isTradesLoading: boolean;
  loadEquity: () => Promise<void>;
  loadMoreRuns: () => Promise<void>;
  loadMoreTrades: () => Promise<void>;
  refreshConfiguration: () => Promise<void>;
  refreshRuns: () => Promise<void>;
  report: HistoricalAnalysisReport | null;
  reportError: string | null;
  runs: HistoricalAnalysisRun[];
  runsNextCursor: string | null;
  selectedRun: HistoricalAnalysisRun | null;
  selectedRunId: string | null;
  clearSelectedRun: () => void;
  selectRun: (runId: string) => void;
  cancelRun: () => Promise<boolean>;
  createRun: (
    request: HistoricalAnalysisCreateRequest,
    idempotencyKey: string,
  ) => Promise<HistoricalAnalysisRun>;
  trades: HistoricalAnalysisTrade[];
  tradesError: string | null;
  tradesNextCursor: string | null;
};

export function useHistoricalAnalyses({
  authStatus,
  csrfToken,
  refreshSession,
}: UseHistoricalAnalysesOptions): HistoricalAnalysesState {
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const [configuration, setConfiguration] =
    useState<HistoricalAnalysisConfiguration | null>(null);
  const [configurationError, setConfigurationError] = useState<string | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [equity, setEquity] = useState<HistoricalAnalysisEquityPoint[]>([]);
  const [equityError, setEquityError] = useState<string | null>(null);
  const [equityNextCursor, setEquityNextCursor] = useState<string | null>(null);
  const [hasLoadedEquity, setHasLoadedEquity] = useState(false);
  const [hasLoadedTrades, setHasLoadedTrades] = useState(false);
  const [isConfigurationLoading, setIsConfigurationLoading] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isEquityLoading, setIsEquityLoading] = useState(false);
  const [isLoadingMoreRuns, setIsLoadingMoreRuns] = useState(false);
  const [isReportLoading, setIsReportLoading] = useState(false);
  const [isRunsLoading, setIsRunsLoading] = useState(false);
  const [isTradesLoading, setIsTradesLoading] = useState(false);
  const [report, setReport] = useState<HistoricalAnalysisReport | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [runs, setRuns] = useState<HistoricalAnalysisRun[]>([]);
  const [runsNextCursor, setRunsNextCursor] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] =
    useState<HistoricalAnalysisRun | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [trades, setTrades] = useState<HistoricalAnalysisTrade[]>([]);
  const [tradesError, setTradesError] = useState<string | null>(null);
  const [tradesNextCursor, setTradesNextCursor] = useState<string | null>(null);

  const configurationRequestInFlight = useRef(false);
  const detailRequestInFlight = useRef(false);
  const equityRequestInFlight = useRef(false);
  const reportRequestInFlight = useRef(false);
  const runsRequestInFlight = useRef(false);
  const selectedRunIdRef = useRef<string | null>(null);
  const tradesRequestInFlight = useRef(false);

  const requestErrorMessage = useCallback(
    async (requestError: unknown): Promise<string> => {
      if (isHistoricalAnalysisAuthenticationError(requestError)) {
        await refreshSession();
      }
      return historicalAnalysisErrorMessage(requestError);
    },
    [refreshSession],
  );

  const resetReportSeries = useCallback(() => {
    setReport(null);
    setReportError(null);
    setTrades([]);
    setTradesError(null);
    setTradesNextCursor(null);
    setHasLoadedTrades(false);
    setEquity([]);
    setEquityError(null);
    setEquityNextCursor(null);
    setHasLoadedEquity(false);
  }, []);

  const refreshConfiguration = useCallback(async () => {
    if (authStatus !== "authenticated" || configurationRequestInFlight.current) {
      return;
    }

    configurationRequestInFlight.current = true;
    setIsConfigurationLoading(true);
    setConfigurationError(null);

    try {
      setConfiguration(await getHistoricalAnalysisConfiguration());
    } catch (requestError) {
      setConfiguration(null);
      setConfigurationError(await requestErrorMessage(requestError));
    } finally {
      configurationRequestInFlight.current = false;
      setIsConfigurationLoading(false);
    }
  }, [authStatus, requestErrorMessage]);

  const refreshRuns = useCallback(async () => {
    if (authStatus !== "authenticated" || runsRequestInFlight.current) {
      return;
    }

    runsRequestInFlight.current = true;
    setIsRunsLoading(true);
    setError(null);

    try {
      const response = await getHistoricalAnalyses();
      setRuns(response.runs);
      setRunsNextCursor(response.nextCursor);
    } catch (requestError) {
      setError(await requestErrorMessage(requestError));
    } finally {
      runsRequestInFlight.current = false;
      setIsRunsLoading(false);
    }
  }, [authStatus, requestErrorMessage]);

  const loadMoreRuns = useCallback(async () => {
    if (
      authStatus !== "authenticated" ||
      !runsNextCursor ||
      runsRequestInFlight.current
    ) {
      return;
    }

    runsRequestInFlight.current = true;
    setIsLoadingMoreRuns(true);
    setError(null);

    try {
      const response = await getHistoricalAnalyses(runsNextCursor);
      setRuns((current) => {
        const existingIds = new Set(current.map((run) => run.id));
        return [
          ...current,
          ...response.runs.filter((run) => !existingIds.has(run.id)),
        ];
      });
      setRunsNextCursor(response.nextCursor);
    } catch (requestError) {
      setError(await requestErrorMessage(requestError));
    } finally {
      runsRequestInFlight.current = false;
      setIsLoadingMoreRuns(false);
    }
  }, [authStatus, requestErrorMessage, runsNextCursor]);

  const loadReport = useCallback(
    async (runId: string) => {
      if (
        authStatus !== "authenticated" ||
        reportRequestInFlight.current ||
        selectedRunIdRef.current !== runId
      ) {
        return;
      }

      reportRequestInFlight.current = true;
      setIsReportLoading(true);
      setReportError(null);

      try {
        const response = await getHistoricalAnalysisReport(runId);
        if (selectedRunIdRef.current === runId) {
          setReport(response.report);
        }
      } catch (requestError) {
        if (selectedRunIdRef.current === runId) {
          setReport(null);
          setReportError(await requestErrorMessage(requestError));
        }
      } finally {
        reportRequestInFlight.current = false;
        setIsReportLoading(false);
      }
    },
    [authStatus, requestErrorMessage],
  );

  const refreshSelectedRun = useCallback(
    async (runId: string) => {
      if (
        authStatus !== "authenticated" ||
        detailRequestInFlight.current ||
        selectedRunIdRef.current !== runId
      ) {
        return;
      }

      detailRequestInFlight.current = true;

      try {
        const response = await getHistoricalAnalysis(runId);
        if (selectedRunIdRef.current !== runId) {
          return;
        }

        setSelectedRun(response.run);
        setRuns((current) =>
          current.map((run) => (run.id === runId ? response.run : run)),
        );
        if (response.run.status === "succeeded") {
          await loadReport(runId);
        } else {
          resetReportSeries();
        }
      } catch (requestError) {
        if (selectedRunIdRef.current === runId) {
          setError(await requestErrorMessage(requestError));
        }
      } finally {
        detailRequestInFlight.current = false;
      }
    },
    [
      authStatus,
      loadReport,
      requestErrorMessage,
      resetReportSeries,
    ],
  );

  const selectRun = useCallback(
    (runId: string) => {
      selectedRunIdRef.current = runId;
      setSelectedRunId(runId);
      setSelectedRun(runs.find((run) => run.id === runId) ?? null);
      resetReportSeries();
      setError(null);
      void refreshSelectedRun(runId);
    },
    [refreshSelectedRun, resetReportSeries, runs],
  );

  const clearSelectedRun = useCallback(() => {
    selectedRunIdRef.current = null;
    setSelectedRunId(null);
    setSelectedRun(null);
    resetReportSeries();
    setError(null);
    setAnnouncement(null);
  }, [resetReportSeries]);

  const createRun = useCallback(
    async (
      request: HistoricalAnalysisCreateRequest,
      idempotencyKey: string,
    ): Promise<HistoricalAnalysisRun> => {
      if (!csrfToken) {
        const authenticationError = new Error("Authentication is required.");
        setError(historicalAnalysisErrorMessage(authenticationError));
        throw authenticationError;
      }

      setError(null);
      setAnnouncement(null);

      try {
        const response = await createHistoricalAnalysis(
          csrfToken,
          idempotencyKey,
          request,
        );
        const run = response.run;
        setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);
        selectedRunIdRef.current = run.id;
        setSelectedRunId(run.id);
        setSelectedRun(run);
        resetReportSeries();
        setAnnouncement("Historical analysis queued.");
        return run;
      } catch (requestError) {
        setError(await requestErrorMessage(requestError));
        throw requestError;
      }
    },
    [csrfToken, requestErrorMessage, resetReportSeries],
  );

  const cancelRun = useCallback(async () => {
    const runId = selectedRunIdRef.current;
    if (!csrfToken || !runId || isCancelling) {
      return false;
    }

    setIsCancelling(true);
    setError(null);
    setAnnouncement(null);

    try {
      const response = await cancelHistoricalAnalysis(csrfToken, runId);
      if (selectedRunIdRef.current === runId) {
        setSelectedRun(response.run);
      }
      setRuns((current) =>
        current.map((run) => (run.id === runId ? response.run : run)),
      );
      setAnnouncement("Analysis cancellation requested.");
      return true;
    } catch (requestError) {
      setError(await requestErrorMessage(requestError));
      return false;
    } finally {
      setIsCancelling(false);
    }
  }, [csrfToken, isCancelling, requestErrorMessage]);

  const loadMoreTrades = useCallback(async () => {
    const runId = selectedRunIdRef.current;
    if (
      authStatus !== "authenticated" ||
      !runId ||
      tradesRequestInFlight.current ||
      (hasLoadedTrades && !tradesNextCursor)
    ) {
      return;
    }

    const cursor = tradesNextCursor ?? undefined;
    tradesRequestInFlight.current = true;
    setIsTradesLoading(true);
    setTradesError(null);

    try {
      const response = await getHistoricalAnalysisTrades(runId, cursor);
      if (selectedRunIdRef.current === runId) {
        setTrades((current) => (cursor ? [...current, ...response.trades] : response.trades));
        setTradesNextCursor(response.nextCursor);
        setHasLoadedTrades(true);
      }
    } catch (requestError) {
      if (selectedRunIdRef.current === runId) {
        setTradesError(await requestErrorMessage(requestError));
      }
    } finally {
      tradesRequestInFlight.current = false;
      setIsTradesLoading(false);
    }
  }, [authStatus, hasLoadedTrades, requestErrorMessage, tradesNextCursor]);

  const loadEquity = useCallback(async () => {
    const runId = selectedRunIdRef.current;
    if (
      authStatus !== "authenticated" ||
      !runId ||
      equityRequestInFlight.current ||
      (hasLoadedEquity && !equityNextCursor)
    ) {
      return;
    }

    const cursor = equityNextCursor ?? undefined;
    equityRequestInFlight.current = true;
    setIsEquityLoading(true);
    setEquityError(null);

    try {
      const response = await getHistoricalAnalysisEquity(runId, cursor);
      if (selectedRunIdRef.current === runId) {
        setEquity((current) => (cursor ? [...current, ...response.equity] : response.equity));
        setEquityNextCursor(response.nextCursor);
        setHasLoadedEquity(true);
      }
    } catch (requestError) {
      if (selectedRunIdRef.current === runId) {
        setEquityError(await requestErrorMessage(requestError));
      }
    } finally {
      equityRequestInFlight.current = false;
      setIsEquityLoading(false);
    }
  }, [authStatus, equityNextCursor, hasLoadedEquity, requestErrorMessage]);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      selectedRunIdRef.current = null;
      setAnnouncement(null);
      setConfiguration(null);
      setConfigurationError(null);
      setError(null);
      setEquity([]);
      setEquityError(null);
      setEquityNextCursor(null);
      setHasLoadedEquity(false);
      setReport(null);
      setReportError(null);
      setRuns([]);
      setRunsNextCursor(null);
      setSelectedRun(null);
      setSelectedRunId(null);
      setTrades([]);
      setTradesError(null);
      setTradesNextCursor(null);
      setHasLoadedTrades(false);
      return;
    }

    void refreshConfiguration();
    void refreshRuns();
  }, [authStatus, refreshConfiguration, refreshRuns]);

  useEffect(() => {
    if (
      authStatus !== "authenticated" ||
      !selectedRunId ||
      !selectedRun ||
      selectedRun.status === "succeeded" ||
      selectedRun.status === "failed" ||
      selectedRun.status === "cancelled"
    ) {
      return;
    }

    let intervalId: number | null = null;

    const stopPolling = () => {
      if (intervalId !== null) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    };

    const startPolling = () => {
      if (document.visibilityState !== "visible" || intervalId !== null) {
        return;
      }
      void refreshSelectedRun(selectedRunId);
      intervalId = window.setInterval(() => {
        void refreshSelectedRun(selectedRunId);
      }, 5_000);
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        stopPolling();
        return;
      }
      startPolling();
    };

    startPolling();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [
    authStatus,
    refreshSelectedRun,
    selectedRun?.cancellationRequested,
    selectedRun?.status,
    selectedRunId,
  ]);

  return {
    announcement,
    configuration,
    configurationError,
    error,
    equity,
    equityError,
    equityNextCursor,
    hasLoadedEquity,
    hasLoadedTrades,
    isConfigurationLoading,
    isCancelling,
    isEquityLoading,
    isLoadingMoreRuns,
    isReportLoading,
    isRunsLoading,
    isTradesLoading,
    loadEquity,
    loadMoreRuns,
    loadMoreTrades,
    refreshConfiguration,
    refreshRuns,
    report,
    reportError,
    runs,
    runsNextCursor,
    selectedRun,
    selectedRunId,
    clearSelectedRun,
    selectRun,
    cancelRun,
    createRun,
    trades,
    tradesError,
    tradesNextCursor,
  };
}
