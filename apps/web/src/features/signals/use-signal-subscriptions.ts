"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import {
  disableSignalSubscription,
  enableSignalSubscription,
  getSignalSubscriptions,
} from "./api";
import {
  isSignalAuthenticationError,
  signalErrorMessage,
} from "./errors";
import type {
  EnableSignalSubscriptionRequest,
  SignalPreset,
  SignalSubscription,
} from "./types";

type UseSignalSubscriptionsOptions = {
  authStatus: AuthStatus;
  csrfToken: string | null;
  refreshSession: () => Promise<void>;
  onSubscriptionChanged: () => Promise<void>;
};

export type SignalSubscriptionsState = {
  subscriptions: SignalSubscription[];
  error: string | null;
  announcement: string | null;
  isLoading: boolean;
  pendingKeys: Set<string>;
  confirmingDisableId: string | null;
  refresh: () => Promise<boolean>;
  subscribe: (symbol: string, preset: SignalPreset) => Promise<boolean>;
  askToDisable: (subscriptionId: string) => void;
  cancelDisable: () => void;
  disable: (subscription: SignalSubscription) => Promise<boolean>;
};

function subscriptionKey(symbol: string, preset: SignalPreset): string {
  return `${symbol}:${preset.code}:${preset.version}`;
}

function mergeSubscription(
  current: SignalSubscription[],
  incoming: SignalSubscription,
): SignalSubscription[] {
  return [incoming, ...current.filter((item) => item.id !== incoming.id)];
}

function updateDisabledSubscription(
  current: SignalSubscription[],
  subscriptionId: string,
): SignalSubscription[] {
  return current.map((subscription) =>
    subscription.id === subscriptionId
      ? {
          ...subscription,
          status: "disabled",
          statusReason: "user_disabled",
          disabledAt: new Date().toISOString(),
        }
      : subscription,
  );
}

export function useSignalSubscriptions({
  authStatus,
  csrfToken,
  refreshSession,
  onSubscriptionChanged,
}: UseSignalSubscriptionsOptions): SignalSubscriptionsState {
  const [subscriptions, setSubscriptions] = useState<SignalSubscription[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingKeys, setPendingKeys] = useState<Set<string>>(new Set());
  const [confirmingDisableId, setConfirmingDisableId] = useState<string | null>(
    null,
  );
  const requestInFlightRef = useRef(false);
  const onSubscriptionChangedRef = useRef(onSubscriptionChanged);

  useEffect(() => {
    onSubscriptionChangedRef.current = onSubscriptionChanged;
  }, [onSubscriptionChanged]);

  const handleError = useCallback(
    async (requestError: unknown) => {
      if (isSignalAuthenticationError(requestError)) {
        await refreshSession();
      }
      setError(signalErrorMessage(requestError));
      setAnnouncement(null);
    },
    [refreshSession],
  );

  const refresh = useCallback(async (): Promise<boolean> => {
    if (authStatus !== "authenticated" || requestInFlightRef.current) {
      return false;
    }

    requestInFlightRef.current = true;
    setIsLoading(true);
    setError(null);
    setAnnouncement(null);

    try {
      const response = await getSignalSubscriptions();
      setSubscriptions(response.subscriptions);
      return true;
    } catch (requestError) {
      await handleError(requestError);
      return false;
    } finally {
      requestInFlightRef.current = false;
      setIsLoading(false);
    }
  }, [authStatus, handleError]);

  const subscribe = useCallback(
    async (symbol: string, preset: SignalPreset): Promise<boolean> => {
      if (!csrfToken) {
        return false;
      }

      const key = subscriptionKey(symbol, preset);
      if (pendingKeys.has(key)) {
        return false;
      }

      setPendingKeys((current) => new Set(current).add(key));
      setError(null);
      setAnnouncement(null);

      const request: EnableSignalSubscriptionRequest = {
        exchange: "binance",
        market_type: "spot",
        symbol,
        preset_code: preset.code,
        preset_version: preset.version,
      };

      try {
        const response = await enableSignalSubscription(csrfToken, request);
        setSubscriptions((current) =>
          mergeSubscription(current, response.subscription),
        );
        setAnnouncement("Signal subscribed.");
        await onSubscriptionChangedRef.current();
        return true;
      } catch (requestError) {
        await handleError(requestError);
        return false;
      } finally {
        setPendingKeys((current) => {
          const next = new Set(current);
          next.delete(key);
          return next;
        });
      }
    },
    [csrfToken, handleError, pendingKeys],
  );

  const askToDisable = useCallback((subscriptionId: string) => {
    setConfirmingDisableId(subscriptionId);
  }, []);

  const cancelDisable = useCallback(() => {
    setConfirmingDisableId(null);
  }, []);

  const disable = useCallback(
    async (subscription: SignalSubscription): Promise<boolean> => {
      if (!csrfToken) {
        return false;
      }

      const key = `${subscription.market.symbol}:${subscription.preset.code}:${subscription.preset.version}`;
      if (pendingKeys.has(key)) {
        return false;
      }

      setPendingKeys((current) => new Set(current).add(key));
      setError(null);
      setAnnouncement(null);

      try {
        await disableSignalSubscription(csrfToken, subscription.id);
        setSubscriptions((current) =>
          updateDisabledSubscription(current, subscription.id),
        );
        setConfirmingDisableId(null);
        setAnnouncement("Signal disabled.");
        await onSubscriptionChangedRef.current();
        return true;
      } catch (requestError) {
        await handleError(requestError);
        return false;
      } finally {
        setPendingKeys((current) => {
          const next = new Set(current);
          next.delete(key);
          return next;
        });
      }
    },
    [csrfToken, handleError, pendingKeys],
  );

  useEffect(() => {
    if (authStatus === "authenticated") {
      void refresh();
      return;
    }

    setSubscriptions([]);
    setError(null);
    setAnnouncement(null);
    setIsLoading(false);
    setPendingKeys(new Set());
    setConfirmingDisableId(null);
  }, [authStatus, refresh]);

  return {
    subscriptions,
    error,
    announcement,
    isLoading,
    pendingKeys,
    confirmingDisableId,
    refresh,
    subscribe,
    askToDisable,
    cancelDisable,
    disable,
  };
}
