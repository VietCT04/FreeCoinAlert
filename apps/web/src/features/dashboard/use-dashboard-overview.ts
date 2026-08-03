"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import { listPriceAlerts } from "../alerts/api";
import type { PriceAlert } from "../alerts/types";
import { getSupportedMarkets } from "../markets/api";
import { getTelegramConnection } from "../telegram/api";
import type { TelegramConnection } from "../telegram/types";
import { getSignalFeed, getSignalSubscriptions } from "../signals/api";
import type { SignalFeedEvent } from "../signals/types";
import type {
  DashboardActivityItem,
  DashboardActivityState,
  DashboardMarketReadiness,
  DashboardMetric,
  DashboardOverviewState,
} from "./types";

type UseDashboardOverviewOptions = {
  authStatus: AuthStatus;
  refreshSession: () => Promise<void>;
};

const EMPTY_ACTIVITY: DashboardActivityState = {
  items: [],
  error: null,
  hasPartialFailure: false,
  isLoading: false,
};

function emptyMetric<T>(): DashboardMetric<T> {
  return { value: null, error: null, isLoading: false };
}

function getInitialState(): Omit<DashboardOverviewState, "refresh"> {
  return {
    activeAlerts: emptyMetric<number>(),
    activeSubscriptions: emptyMetric<number>(),
    telegram: emptyMetric<TelegramConnection>(),
    markets: emptyMetric<DashboardMarketReadiness>(),
    activity: EMPTY_ACTIVITY,
    isRefreshing: false,
  };
}

function requestStatus(error: unknown): number | undefined {
  if (typeof error !== "object" || error === null || !("status" in error)) {
    return undefined;
  }

  const status = error.status;
  return typeof status === "number" ? status : undefined;
}

function isAuthenticationError(error: unknown): boolean {
  if (requestStatus(error) === 401) {
    return true;
  }

  if (typeof error !== "object" || error === null || !("code" in error)) {
    return false;
  }

  return error.code === "AUTHENTICATION_REQUIRED";
}

function safeErrorMessage(error: unknown): string {
  return isAuthenticationError(error)
    ? "Your session has ended. Please sign in again."
    : "This information is temporarily unavailable. Please try again.";
}

function metricFromResult<T, V>(
  result: PromiseSettledResult<T>,
  select: (value: T) => V,
): DashboardMetric<V> {
  if (result.status === "fulfilled") {
    return { value: select(result.value), error: null, isLoading: false };
  }

  return {
    value: null,
    error: safeErrorMessage(result.reason),
    isLoading: false,
  };
}

function formatDirection(direction: PriceAlert["direction"]): string {
  return direction === "cross_above" ? "above" : "below";
}

function toPriceAlertActivity(alert: PriceAlert): DashboardActivityItem | null {
  if (!alert.trigger) {
    return null;
  }

  return {
    id: `price-alert:${alert.id}`,
    kind: "price_alert_triggered",
    title: "Price alert triggered",
    description: `${alert.market.symbol} crossed ${formatDirection(alert.direction)} ${alert.targetPrice} ${alert.market.quoteAsset}.`,
    occurredAt: alert.trigger.occurredAt,
    href: "/price-alerts",
    statusLabel: "Triggered",
  };
}

function toSignalActivity(event: SignalFeedEvent): DashboardActivityItem {
  const invalidated = event.status === "invalidated";

  return {
    id: `signal:${event.id}`,
    kind: invalidated ? "signal_invalidated" : "signal_occurred",
    title: invalidated ? "Signal invalidated" : "Signal occurred",
    description: `${event.market.symbol} · ${event.preset.name}.`,
    occurredAt: event.occurredAt,
    href: "/preset-signals",
    statusLabel: invalidated ? "Invalidated" : "Occurred",
  };
}

function sortActivity(items: DashboardActivityItem[]): DashboardActivityItem[] {
  return [...items]
    .sort((left, right) => {
      const byTime = right.occurredAt.localeCompare(left.occurredAt);
      return byTime === 0 ? right.id.localeCompare(left.id) : byTime;
    })
    .slice(0, 5);
}

function activityFromResults(
  alertResult: PromiseSettledResult<{ alerts: PriceAlert[] }>,
  signalResult: PromiseSettledResult<Awaited<ReturnType<typeof getSignalFeed>>>,
): DashboardActivityState {
  const alerts =
    alertResult.status === "fulfilled"
      ? alertResult.value.alerts.flatMap((alert) => {
          const item = toPriceAlertActivity(alert);
          return item ? [item] : [];
        })
      : [];
  const signals =
    signalResult.status === "fulfilled"
      ? signalResult.value.events.map(toSignalActivity)
      : [];
  const failedRequests = [alertResult, signalResult].filter(
    (result) => result.status === "rejected",
  ).length;

  return {
    items: sortActivity([...alerts, ...signals]),
    error:
      failedRequests === 0
        ? null
        : failedRequests === 2
          ? "Recent activity is temporarily unavailable. Please try again."
          : "Some recent activity is temporarily unavailable.",
    hasPartialFailure: failedRequests === 1,
    isLoading: false,
  };
}

export function useDashboardOverview({
  authStatus,
  refreshSession,
}: UseDashboardOverviewOptions): DashboardOverviewState {
  const [state, setState] = useState(getInitialState);
  const requestInFlight = useRef(false);
  const requestVersion = useRef(0);

  const refresh = useCallback(async () => {
    if (authStatus !== "authenticated" || requestInFlight.current) {
      return;
    }

    requestInFlight.current = true;
    const version = ++requestVersion.current;
    setState((current) => ({
      ...current,
      activeAlerts: { ...current.activeAlerts, error: null, isLoading: true },
      activeSubscriptions: {
        ...current.activeSubscriptions,
        error: null,
        isLoading: true,
      },
      telegram: { ...current.telegram, error: null, isLoading: true },
      markets: { ...current.markets, error: null, isLoading: true },
      activity: { ...current.activity, error: null, isLoading: true },
      isRefreshing: true,
    }));

    try {
      const [
        activeAlertsResult,
        subscriptionsResult,
        telegramResult,
        marketsResult,
        triggeredAlertsResult,
        signalFeedResult,
      ] = await Promise.allSettled([
        listPriceAlerts({ status: "active", limit: 20 }),
        getSignalSubscriptions(),
        getTelegramConnection(),
        getSupportedMarkets(),
        listPriceAlerts({ status: "triggered", limit: 5 }),
        getSignalFeed({ status: "all", limit: 5 }),
      ]);

      if (version !== requestVersion.current) {
        return;
      }

      const authenticationFailed = [
        activeAlertsResult,
        subscriptionsResult,
        telegramResult,
        marketsResult,
        triggeredAlertsResult,
        signalFeedResult,
      ].some(
        (result) =>
          result.status === "rejected" && isAuthenticationError(result.reason),
      );

      setState({
        activeAlerts: metricFromResult(
          activeAlertsResult,
          (response) => response.alerts.length,
        ),
        activeSubscriptions: metricFromResult(
          subscriptionsResult,
          (response) =>
            response.subscriptions.filter(
              (subscription) => subscription.status === "active",
            ).length,
        ),
        telegram: metricFromResult(telegramResult, (response) => response.connection),
        markets: metricFromResult(marketsResult, (response) => ({
          available: response.markets.filter((market) => market.status === "available").length,
          total: response.markets.length,
        })),
        activity: activityFromResults(triggeredAlertsResult, signalFeedResult),
        isRefreshing: false,
      });

      if (authenticationFailed) {
        await refreshSession();
      }
    } finally {
      requestInFlight.current = false;
      if (version === requestVersion.current) {
        setState((current) => ({ ...current, isRefreshing: false }));
      }
    }
  }, [authStatus, refreshSession]);

  useEffect(() => {
    if (authStatus === "authenticated") {
      void refresh();
      return;
    }

    requestVersion.current += 1;
    requestInFlight.current = false;
    setState(getInitialState());
  }, [authStatus, refresh]);

  return { ...state, refresh };
}
