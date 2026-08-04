"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import { listPriceAlerts, PriceAlertApiError } from "../alerts/api";
import { getSignalSubscriptions } from "../signals/api";
import { SignalApiError } from "../signals/errors";

type UseTelegramUsageSummaryOptions = {
  authStatus: AuthStatus;
  refreshSession: () => Promise<void>;
};

export type TelegramUsageSummaryState = {
  activePriceAlerts: number | null;
  activePresetSubscriptions: number | null;
  priceAlertsError: string | null;
  presetSubscriptionsError: string | null;
  isLoading: boolean;
  refresh: () => Promise<void>;
};

function isAuthenticationError(error: unknown): boolean {
  return (
    (error instanceof PriceAlertApiError || error instanceof SignalApiError) &&
    (error.status === 401 || error.code === "AUTHENTICATION_REQUIRED")
  );
}

export function useTelegramUsageSummary({
  authStatus,
  refreshSession,
}: UseTelegramUsageSummaryOptions): TelegramUsageSummaryState {
  const [activePriceAlerts, setActivePriceAlerts] = useState<number | null>(null);
  const [activePresetSubscriptions, setActivePresetSubscriptions] = useState<number | null>(
    null,
  );
  const [priceAlertsError, setPriceAlertsError] = useState<string | null>(null);
  const [presetSubscriptionsError, setPresetSubscriptionsError] = useState<string | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const requestInFlight = useRef(false);

  const refresh = useCallback(async () => {
    if (authStatus !== "authenticated" || requestInFlight.current) return;

    requestInFlight.current = true;
    setIsLoading(true);
    setActivePriceAlerts(null);
    setActivePresetSubscriptions(null);
    setPriceAlertsError(null);
    setPresetSubscriptionsError(null);

    try {
      const [priceAlertsResult, subscriptionsResult] = await Promise.allSettled([
        listPriceAlerts({ status: "active", limit: 20 }),
        getSignalSubscriptions(),
      ]);

      if (priceAlertsResult.status === "fulfilled") {
        setActivePriceAlerts(priceAlertsResult.value.alerts.length);
      } else {
        setPriceAlertsError("Active price-alert usage is unavailable right now.");
      }

      if (subscriptionsResult.status === "fulfilled") {
        setActivePresetSubscriptions(
          subscriptionsResult.value.subscriptions.filter(
            (subscription) =>
              subscription.status === "active" &&
              subscription.telegramDelivery.enabled,
          ).length,
        );
      } else {
        setPresetSubscriptionsError(
          "Active preset-subscription usage is unavailable right now.",
        );
      }

      const authenticationFailed = [priceAlertsResult, subscriptionsResult].some(
        (result) =>
          result.status === "rejected" && isAuthenticationError(result.reason),
      );
      if (authenticationFailed) {
        await refreshSession();
      }
    } finally {
      requestInFlight.current = false;
      setIsLoading(false);
    }
  }, [authStatus, refreshSession]);

  useEffect(() => {
    if (authStatus === "authenticated") {
      void refresh();
      return;
    }

    setActivePriceAlerts(null);
    setActivePresetSubscriptions(null);
    setPriceAlertsError(null);
    setPresetSubscriptionsError(null);
    setIsLoading(false);
  }, [authStatus, refresh]);

  return {
    activePriceAlerts,
    activePresetSubscriptions,
    priceAlertsError,
    presetSubscriptionsError,
    isLoading,
    refresh,
  };
}
