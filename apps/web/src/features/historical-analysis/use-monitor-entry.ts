"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import {
  enableSignalSubscription,
  getSignalPresets,
  getSignalSubscriptions,
  setSignalTelegramDelivery,
} from "../signals/api";
import {
  SignalApiError,
  isSignalAuthenticationError,
  signalErrorMessage,
} from "../signals/errors";
import type {
  SignalPreset,
  SignalSubscription,
} from "../signals/types";
import type {
  HistoricalAnalysisReport,
  HistoricalAnalysisStatus,
} from "./types";

type UseMonitorEntryOptions = {
  authStatus: AuthStatus;
  csrfToken: string | null;
  refreshSession: () => Promise<void>;
  report: HistoricalAnalysisReport | null;
  runStatus: HistoricalAnalysisStatus | null;
};

export type MonitorEntryState = {
  activePreset: SignalPreset | null;
  errorCode: string | null;
  error: string | null;
  isLoading: boolean;
  isMonitorPending: boolean;
  isTelegramPending: boolean;
  monitorConfirmationOpen: boolean;
  subscription: SignalSubscription | null;
  telegramConfirmationOpen: boolean;
  refresh: () => Promise<boolean>;
  askToMonitor: () => void;
  cancelMonitorConfirmation: () => void;
  startMonitoring: () => Promise<boolean>;
  askToEnableTelegram: () => void;
  cancelTelegramConfirmation: () => void;
  enableTelegram: () => Promise<boolean>;
};

function matchesReportSubscription(
  subscription: SignalSubscription,
  report: HistoricalAnalysisReport,
): boolean {
  return (
    subscription.market.exchange === report.market.exchange &&
    subscription.market.marketType === report.market.marketType &&
    subscription.market.symbol === report.market.symbol &&
    subscription.preset.code === report.preset.code &&
    subscription.preset.version === report.preset.version
  );
}

export function useMonitorEntry({
  authStatus,
  csrfToken,
  refreshSession,
  report,
  runStatus,
}: UseMonitorEntryOptions): MonitorEntryState {
  const [activePreset, setActivePreset] = useState<SignalPreset | null>(null);
  const [subscription, setSubscription] = useState<SignalSubscription | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isMonitorPending, setIsMonitorPending] = useState(false);
  const [isTelegramPending, setIsTelegramPending] = useState(false);
  const [monitorConfirmationOpen, setMonitorConfirmationOpen] = useState(false);
  const [telegramConfirmationOpen, setTelegramConfirmationOpen] = useState(false);
  const requestInFlight = useRef(false);

  const reportIsEligible =
    authStatus === "authenticated" &&
    runStatus === "succeeded" &&
    report !== null &&
    report.market.exchange === "binance" &&
    report.market.marketType === "spot";
  const reportId = report?.reportId ?? null;

  const refresh = useCallback(async (): Promise<boolean> => {
    if (!reportIsEligible || !report || requestInFlight.current) {
      return false;
    }

    requestInFlight.current = true;
    setIsLoading(true);
    setError(null);
    setErrorCode(null);

    try {
      const [presetResponse, subscriptionResponse] = await Promise.all([
        getSignalPresets(),
        getSignalSubscriptions(),
      ]);
      const matchingPreset = presetResponse.presets.find(
        (preset) =>
          preset.code === report.preset.code &&
          preset.version === report.preset.version,
      );

      setActivePreset(matchingPreset ?? null);
      setSubscription(
        matchingPreset
          ? subscriptionResponse.subscriptions.find((item) =>
              matchesReportSubscription(item, report),
            ) ?? null
          : null,
      );
      return true;
    } catch (requestError) {
      if (isSignalAuthenticationError(requestError)) {
        await refreshSession();
      }
      setActivePreset(null);
      setSubscription(null);
      setErrorCode(
        requestError instanceof SignalApiError ? requestError.code ?? null : null,
      );
      setError(signalErrorMessage(requestError));
      return false;
    } finally {
      requestInFlight.current = false;
      setIsLoading(false);
    }
  }, [refreshSession, report, reportIsEligible]);

  useEffect(() => {
    setMonitorConfirmationOpen(false);
    setTelegramConfirmationOpen(false);
    setActivePreset(null);
    setSubscription(null);
    setError(null);
    setErrorCode(null);

    if (reportIsEligible) {
      void refresh();
    }
  }, [refresh, reportId, reportIsEligible]);

  const askToMonitor = useCallback(() => {
    if (activePreset && subscription?.status !== "active") {
      setError(null);
      setErrorCode(null);
      setMonitorConfirmationOpen(true);
    }
  }, [activePreset, subscription]);

  const cancelMonitorConfirmation = useCallback(() => {
    if (!isMonitorPending) {
      setMonitorConfirmationOpen(false);
    }
  }, [isMonitorPending]);

  const startMonitoring = useCallback(async (): Promise<boolean> => {
    if (
      !csrfToken ||
      !reportIsEligible ||
      !report ||
      !activePreset ||
      subscription?.status === "active" ||
      isMonitorPending
    ) {
      return false;
    }

    setIsMonitorPending(true);
    setError(null);
    setErrorCode(null);

    try {
      const response = await enableSignalSubscription(csrfToken, {
        exchange: "binance",
        market_type: "spot",
        symbol: report.market.symbol,
        preset_code: report.preset.code,
        preset_version: report.preset.version,
      });
      setSubscription(response.subscription);
      setMonitorConfirmationOpen(false);
      return true;
    } catch (requestError) {
      if (isSignalAuthenticationError(requestError)) {
        await refreshSession();
      }
      setErrorCode(
        requestError instanceof SignalApiError ? requestError.code ?? null : null,
      );
      setError(signalErrorMessage(requestError));
      return false;
    } finally {
      setIsMonitorPending(false);
    }
  }, [
    activePreset,
    csrfToken,
    isMonitorPending,
    refreshSession,
    report,
    reportIsEligible,
    subscription,
  ]);

  const askToEnableTelegram = useCallback(() => {
    if (
      subscription?.status === "active" &&
      !subscription.telegramDelivery.enabled &&
      subscription.telegramDelivery.readiness === "ready"
    ) {
      setError(null);
      setErrorCode(null);
      setTelegramConfirmationOpen(true);
    }
  }, [subscription]);

  const cancelTelegramConfirmation = useCallback(() => {
    if (!isTelegramPending) {
      setTelegramConfirmationOpen(false);
    }
  }, [isTelegramPending]);

  const enableTelegram = useCallback(async (): Promise<boolean> => {
    if (
      !csrfToken ||
      !subscription ||
      subscription.status !== "active" ||
      subscription.telegramDelivery.enabled ||
      subscription.telegramDelivery.readiness !== "ready" ||
      isTelegramPending
    ) {
      return false;
    }

    setIsTelegramPending(true);
    setError(null);
    setErrorCode(null);

    try {
      const response = await setSignalTelegramDelivery(
        csrfToken,
        subscription.id,
        true,
      );
      setSubscription(response.subscription);
      setTelegramConfirmationOpen(false);
      return true;
    } catch (requestError) {
      if (isSignalAuthenticationError(requestError)) {
        await refreshSession();
      }
      setErrorCode(
        requestError instanceof SignalApiError ? requestError.code ?? null : null,
      );
      setError(signalErrorMessage(requestError));
      return false;
    } finally {
      setIsTelegramPending(false);
    }
  }, [csrfToken, isTelegramPending, refreshSession, subscription]);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      setActivePreset(null);
      setSubscription(null);
      setError(null);
      setErrorCode(null);
      setIsLoading(false);
      setMonitorConfirmationOpen(false);
      setTelegramConfirmationOpen(false);
    }
  }, [authStatus]);

  return {
    activePreset,
    errorCode,
    error,
    isLoading,
    isMonitorPending,
    isTelegramPending,
    monitorConfirmationOpen,
    subscription,
    telegramConfirmationOpen,
    refresh,
    askToMonitor,
    cancelMonitorConfirmation,
    startMonitoring,
    askToEnableTelegram,
    cancelTelegramConfirmation,
    enableTelegram,
  };
}
