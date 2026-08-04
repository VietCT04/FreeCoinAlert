"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import { getTelegramConnection } from "../telegram/api";
import type { TelegramConnection } from "../telegram/types";
import { createPriceAlert, deletePriceAlert, listPriceAlerts, PriceAlertApiError } from "./api";
import type {
  CreatePriceAlertRequest,
  PriceAlert,
  PriceAlertStatus,
} from "./types";

const ACTIVE_REFRESH_MS = 30_000;
const PENDING_REFRESH_MS = 2_000;
const PENDING_REFRESH_SLOW_MS = 15_000;
const PENDING_REFRESH_MAX_MS = 60_000;

type UsePriceAlertsOptions = {
  authStatus: AuthStatus;
  csrfToken: string | null;
  refreshSession: () => Promise<void>;
  statusFilter: PriceAlertStatus | "all";
};

export type PriceAlertsState = {
  alerts: PriceAlert[];
  connection: TelegramConnection | null;
  error: string | null;
  hasPendingDeliveryPastLimit: boolean;
  isCreating: boolean;
  isInitialLoading: boolean;
  isLoadingMore: boolean;
  isRefreshing: boolean;
  nextCursor: string | null;
  refreshAlerts: () => Promise<void>;
  loadMore: () => Promise<void>;
  create: (request: CreatePriceAlertRequest) => Promise<boolean>;
  remove: (alertId: string) => Promise<boolean>;
  clearError: () => void;
};

function mergeAlerts(current: PriceAlert[], incoming: PriceAlert[]): PriceAlert[] {
  const updated = new Map(incoming.map((alert) => [alert.id, alert]));
  const retained = current.filter((alert) => !updated.has(alert.id));
  return [...incoming, ...retained];
}

function isPendingDelivery(alert: PriceAlert): boolean {
  return ["queued", "sending", "retrying"].includes(alert.delivery.status);
}

function isAuthenticationError(error: unknown): boolean {
  return error instanceof PriceAlertApiError && (error.status === 401 || error.code === "AUTHENTICATION_REQUIRED");
}

function errorMessage(error: unknown): string {
  if (error instanceof PriceAlertApiError) {
    const retryAfter = error.retryAfter ? ` Try again in ${error.retryAfter} seconds.` : "";
    switch (error.code) {
      case "ALERT_TARGET_INVALID": return "Enter a target that follows this market’s price rules.";
      case "ALERT_MARKET_UNAVAILABLE": return "This market is not available for new alerts.";
      case "ALERT_TELEGRAM_NOT_CONNECTED": return "Connect Telegram before creating an alert.";
      case "ALERT_TELEGRAM_DEGRADED": return "Reconnect Telegram before creating an alert.";
      case "ALERT_ACTIVE_LIMIT_REACHED": return "You already have the maximum of 20 active alerts.";
      case "ALERT_IDEMPOTENCY_CONFLICT": return "This request could not be safely repeated. Review the form and try again.";
      case "ALERT_NOT_DELETABLE": return "This alert can no longer be deleted.";
      case "ALERT_RATE_LIMITED": return `Too many alert requests.${retryAfter}`;
      case "AUTHENTICATION_REQUIRED": return "Your session has ended. Please sign in again.";
      case "AUTH_CSRF_INVALID": return "Your session could not be confirmed. Please refresh and try again.";
      default: break;
    }
  }
  return "We couldn’t complete that alert request. Please try again.";
}

export function usePriceAlerts({
  authStatus,
  csrfToken,
  refreshSession,
  statusFilter,
}: UsePriceAlertsOptions): PriceAlertsState {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [connection, setConnection] = useState<TelegramConnection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasPendingDeliveryPastLimit, setHasPendingDeliveryPastLimit] = useState(false);
  const requestInFlight = useRef(false);
  const createKey = useRef<string | null>(null);
  const createRequestFingerprint = useRef<string | null>(null);
  const pendingStartedAt = useRef<number | null>(null);
  const requestVersion = useRef(0);
  const requestFilter = useRef<PriceAlertStatus | undefined>(undefined);
  const requestedStatus = statusFilter === "all" ? undefined : statusFilter;

  const handleError = useCallback(async (requestError: unknown) => {
    if (isAuthenticationError(requestError)) {
      await refreshSession();
    }
    setError(errorMessage(requestError));
  }, [refreshSession]);

  const refreshAlerts = useCallback(async () => {
    if (authStatus !== "authenticated") return;
    if (requestInFlight.current && requestFilter.current === requestedStatus) {
      return;
    }
    const version = ++requestVersion.current;
    requestFilter.current = requestedStatus;
    requestInFlight.current = true;
    setIsRefreshing(true);
    setError(null);
    try {
      const alertResponse = await listPriceAlerts({
        limit: 20,
        status: requestedStatus,
      });
      if (version !== requestVersion.current) return;
      setAlerts(alertResponse.alerts);
      setNextCursor(alertResponse.nextCursor);
    } catch (requestError) {
      if (version === requestVersion.current) {
        await handleError(requestError);
      }
    } finally {
      if (version === requestVersion.current) {
        requestInFlight.current = false;
        setIsRefreshing(false);
        setIsInitialLoading(false);
      }
    }
  }, [authStatus, handleError, requestedStatus]);

  const loadMore = useCallback(async () => {
    if (authStatus !== "authenticated" || !nextCursor || requestInFlight.current) return;
    const version = ++requestVersion.current;
    requestInFlight.current = true;
    setIsLoadingMore(true);
    setError(null);
    try {
      const response = await listPriceAlerts({
        cursor: nextCursor,
        limit: 20,
        status: requestedStatus,
      });
      if (version !== requestVersion.current) return;
      setAlerts((current) => mergeAlerts(current, response.alerts));
      setNextCursor(response.nextCursor);
    } catch (requestError) {
      if (version === requestVersion.current) {
        await handleError(requestError);
      }
    } finally {
      if (version === requestVersion.current) {
        requestInFlight.current = false;
        setIsLoadingMore(false);
      }
    }
  }, [authStatus, handleError, nextCursor, requestedStatus]);

  const create = useCallback(async (request: CreatePriceAlertRequest): Promise<boolean> => {
    if (!csrfToken || isCreating) return false;
    setIsCreating(true);
    setError(null);
    const requestFingerprint = JSON.stringify(request);
    if (createRequestFingerprint.current !== requestFingerprint) {
      createKey.current = null;
      createRequestFingerprint.current = requestFingerprint;
    }
    createKey.current ??= crypto.randomUUID();
    try {
      const response = await createPriceAlert(csrfToken, createKey.current, request);
      if (statusFilter === "all" || statusFilter === "active") {
        setAlerts((current) => mergeAlerts(current, [response.alert]));
      }
      createKey.current = null;
      createRequestFingerprint.current = null;
      return true;
    } catch (requestError) {
      if (requestError instanceof PriceAlertApiError && requestError.status < 500) {
        createKey.current = null;
        createRequestFingerprint.current = null;
      }
      await handleError(requestError);
      return false;
    } finally {
      setIsCreating(false);
    }
  }, [csrfToken, handleError, isCreating, statusFilter]);

  const remove = useCallback(async (alertId: string): Promise<boolean> => {
    if (!csrfToken) return false;
    setError(null);
    try {
      await deletePriceAlert(csrfToken, alertId);
      setAlerts((current) => current.filter((alert) => alert.id !== alertId));
      return true;
    } catch (requestError) {
      await handleError(requestError);
      if (requestError instanceof PriceAlertApiError && requestError.code === "ALERT_NOT_DELETABLE") void refreshAlerts();
      return false;
    }
  }, [csrfToken, handleError, refreshAlerts]);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      requestVersion.current += 1;
      requestInFlight.current = false;
      requestFilter.current = undefined;
      createKey.current = null;
      createRequestFingerprint.current = null;
      pendingStartedAt.current = null;
      setAlerts([]);
      setConnection(null);
      setError(null);
      setNextCursor(null);
      setIsLoadingMore(false);
      setHasPendingDeliveryPastLimit(false);
      return;
    }
    setAlerts([]);
    setNextCursor(null);
    setIsLoadingMore(false);
    setIsInitialLoading(true);
    void Promise.all([refreshAlerts(), getTelegramConnection()])
      .then(([, response]) => setConnection(response.connection))
      .catch((requestError: unknown) => void handleError(requestError))
      .finally(() => setIsInitialLoading(false));
  }, [authStatus, handleError, refreshAlerts, statusFilter]);

  useEffect(() => {
    const hasPending = alerts.some(isPendingDelivery);
    const hasActive = alerts.some((alert) => alert.status === "active");
    if (!hasPending) { pendingStartedAt.current = null; setHasPendingDeliveryPastLimit(false); }
    if ((!hasPending && !hasActive) || document.hidden) return;
    pendingStartedAt.current ??= Date.now();
    const pendingExpired = hasPending && Date.now() - pendingStartedAt.current >= PENDING_REFRESH_MAX_MS;
    setHasPendingDeliveryPastLimit(pendingExpired);
    const interval = hasPending ? (pendingExpired ? PENDING_REFRESH_SLOW_MS : PENDING_REFRESH_MS) : ACTIVE_REFRESH_MS;
    const id = window.setInterval(() => { if (!document.hidden) void refreshAlerts(); }, interval);
    const onVisible = () => { if (!document.hidden) void refreshAlerts(); };
    document.addEventListener("visibilitychange", onVisible); window.addEventListener("focus", onVisible);
    return () => { window.clearInterval(id); document.removeEventListener("visibilitychange", onVisible); window.removeEventListener("focus", onVisible); };
  }, [alerts, refreshAlerts]);

  return { alerts, connection, error, hasPendingDeliveryPastLimit, isCreating, isInitialLoading, isLoadingMore, isRefreshing, nextCursor, refreshAlerts, loadMore, create, remove, clearError: () => setError(null) };
}
