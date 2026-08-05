"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import { getSignalStreamUrl } from "./api";
import type {
  SignalConnectionStatus,
  SignalFeedEvent,
  SignalInvalidationEvent,
} from "./types";

const STREAM_DISCONNECTED_AFTER_MS = 60_000;
const STREAM_FALLBACK_REFRESH_MS = 30_000;
const MAX_RECENT_STREAM_SEQUENCES = 2_000;

type UseSignalStreamOptions = {
  authStatus: AuthStatus;
  enabled: boolean;
  restartToken: number;
  streamCursor: string | null;
  onSignal: (event: SignalFeedEvent) => void;
  onInvalidation: (event: SignalInvalidationEvent) => boolean;
  recoverHistory: () => Promise<boolean>;
  onAuthExpired: () => void;
};

export type SignalStreamState = {
  status: SignalConnectionStatus;
  reconnect: () => Promise<void>;
};

function parseMessageData(event: Event): unknown | null {
  const message = event as MessageEvent<string>;
  if (typeof message.data !== "string") {
    return null;
  }

  try {
    return JSON.parse(message.data) as unknown;
  } catch {
    return null;
  }
}

function isSignalFeedEvent(value: unknown): value is SignalFeedEvent {
  if (!value || typeof value !== "object") {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    (record.deliveryMode === "live" || record.deliveryMode === "replay") &&
    typeof record.status === "string" &&
    typeof record.market === "object" &&
    typeof record.preset === "object" &&
    typeof record.comparison === "object" &&
    typeof record.candle === "object"
  );
}

function isSignalInvalidationEvent(
  value: unknown,
): value is SignalInvalidationEvent {
  if (!value || typeof value !== "object") {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    typeof record.eventId === "string" &&
    typeof record.reason === "string" &&
    (record.deliveryMode === "live" || record.deliveryMode === "replay")
  );
}

export function useSignalStream({
  authStatus,
  enabled,
  restartToken,
  streamCursor,
  onSignal,
  onInvalidation,
  recoverHistory,
  onAuthExpired,
}: UseSignalStreamOptions): SignalStreamState {
  const [status, setStatus] = useState<SignalConnectionStatus>("connecting");
  const [isVisible, setIsVisible] = useState(true);
  const [connectionVersion, setConnectionVersion] = useState(0);
  const sourceRef = useRef<EventSource | null>(null);
  const recentSequencesRef = useRef<string[]>([]);
  const recentSequenceSetRef = useRef(new Set<string>());
  const disconnectedTimerRef = useRef<number | null>(null);
  const fallbackIntervalRef = useRef<number | null>(null);
  const recoveryInFlightRef = useRef(false);
  const onSignalRef = useRef(onSignal);
  const onInvalidationRef = useRef(onInvalidation);
  const recoverHistoryRef = useRef(recoverHistory);
  const onAuthExpiredRef = useRef(onAuthExpired);

  useEffect(() => {
    onSignalRef.current = onSignal;
    onInvalidationRef.current = onInvalidation;
    recoverHistoryRef.current = recoverHistory;
    onAuthExpiredRef.current = onAuthExpired;
  }, [onAuthExpired, onInvalidation, onSignal, recoverHistory]);

  const clearFallback = useCallback(() => {
    if (disconnectedTimerRef.current !== null) {
      window.clearTimeout(disconnectedTimerRef.current);
      disconnectedTimerRef.current = null;
    }
    if (fallbackIntervalRef.current !== null) {
      window.clearInterval(fallbackIntervalRef.current);
      fallbackIntervalRef.current = null;
    }
  }, []);

  const closeSource = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  const recover = useCallback(async () => {
    if (
      authStatus !== "authenticated" ||
      document.visibilityState !== "visible" ||
      recoveryInFlightRef.current
    ) {
      return;
    }

    recoveryInFlightRef.current = true;
    setStatus("connecting");
    clearFallback();
    closeSource();
    try {
      const recovered = await recoverHistoryRef.current();
      if (recovered && document.visibilityState === "visible") {
        setIsVisible(true);
        setConnectionVersion((current) => current + 1);
      } else {
        setStatus("disconnected");
      }
    } finally {
      recoveryInFlightRef.current = false;
    }
  }, [authStatus, clearFallback, closeSource]);

  const startFallback = useCallback(() => {
    if (
      disconnectedTimerRef.current !== null ||
      document.visibilityState !== "visible"
    ) {
      return;
    }

    disconnectedTimerRef.current = window.setTimeout(() => {
      disconnectedTimerRef.current = null;
      setStatus("disconnected");
      fallbackIntervalRef.current = window.setInterval(() => {
        if (document.visibilityState === "visible") {
          void recover();
        }
      }, STREAM_FALLBACK_REFRESH_MS);
    }, STREAM_DISCONNECTED_AFTER_MS);
  }, [recover]);

  const reconnect = useCallback(async () => {
    await recover();
  }, [recover]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        setIsVisible(false);
        clearFallback();
        closeSource();
        setStatus("disconnected");
        return;
      }

      void recover();
    };

    if (document.visibilityState === "hidden") {
      setIsVisible(false);
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [clearFallback, closeSource, recover]);

  useEffect(() => {
    const handleOffline = () => {
      clearFallback();
      closeSource();
      setIsVisible(false);
      setStatus("reconnecting");
    };
    const handleOnline = () => {
      void recover();
    };

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, [clearFallback, closeSource, recover]);

  useEffect(() => {
    if (
      authStatus !== "authenticated" ||
      !enabled ||
      !streamCursor ||
      !isVisible ||
      document.visibilityState === "hidden"
    ) {
      closeSource();
      clearFallback();
      if (authStatus !== "authenticated") {
        setStatus("disconnected");
      }
      return;
    }

    closeSource();
    clearFallback();
    setStatus("connecting");
    const source = new EventSource(getSignalStreamUrl(streamCursor), {
      withCredentials: true,
    });
    sourceRef.current = source;

    const acceptSequence = (sequence: string): boolean => {
      if (!sequence) {
        return true;
      }
      if (recentSequenceSetRef.current.has(sequence)) {
        return false;
      }
      recentSequenceSetRef.current.add(sequence);
      recentSequencesRef.current.push(sequence);
      while (recentSequencesRef.current.length > MAX_RECENT_STREAM_SEQUENCES) {
        const oldest = recentSequencesRef.current.shift();
        if (oldest) {
          recentSequenceSetRef.current.delete(oldest);
        }
      }
      return true;
    };

    const recoverAfterControlEvent = async (
      nextStatus: SignalConnectionStatus,
    ) => {
      if (sourceRef.current !== source) {
        return;
      }
      closeSource();
      clearFallback();
      setStatus(nextStatus);
      if (recoveryInFlightRef.current) {
        return;
      }
      recoveryInFlightRef.current = true;
      try {
        const recovered = await recoverHistoryRef.current();
        if (recovered && document.visibilityState === "visible") {
          setConnectionVersion((current) => current + 1);
        } else {
          setStatus("disconnected");
        }
      } finally {
        recoveryInFlightRef.current = false;
      }
    };

    source.onopen = () => {
      if (sourceRef.current !== source) {
        return;
      }
      clearFallback();
      setStatus("live");
    };

    source.onerror = () => {
      if (sourceRef.current !== source) {
        return;
      }
      setStatus("reconnecting");
      startFallback();
    };

    const handleSignal = (event: Event) => {
      const message = event as MessageEvent<string>;
      if (!acceptSequence(message.lastEventId)) {
        return;
      }
      const payload = parseMessageData(event);
      if (isSignalFeedEvent(payload)) {
        onSignalRef.current(payload);
      }
    };

    const handleInvalidation = (event: Event) => {
      const message = event as MessageEvent<string>;
      if (!acceptSequence(message.lastEventId)) {
        return;
      }
      const payload = parseMessageData(event);
      if (isSignalInvalidationEvent(payload)) {
        const known = onInvalidationRef.current(payload);
        if (!known && payload.deliveryMode === "live") {
          void recoverAfterControlEvent("history recovery required");
        }
      }
    };

    const handleReset = () => {
      void recoverAfterControlEvent("history recovery required");
    };

    const handleAuthExpired = () => {
      if (sourceRef.current !== source) {
        return;
      }
      closeSource();
      clearFallback();
      setStatus("authentication expired");
      onAuthExpiredRef.current();
    };

    source.addEventListener("signal", handleSignal);
    source.addEventListener("signal_invalidated", handleInvalidation);
    source.addEventListener("reset", handleReset);
    source.addEventListener("auth_expired", handleAuthExpired);

    return () => {
      source.removeEventListener("signal", handleSignal);
      source.removeEventListener("signal_invalidated", handleInvalidation);
      source.removeEventListener("reset", handleReset);
      source.removeEventListener("auth_expired", handleAuthExpired);
      if (sourceRef.current === source) {
        closeSource();
      }
      clearFallback();
    };
  }, [
    authStatus,
    clearFallback,
    closeSource,
    connectionVersion,
    enabled,
    isVisible,
    recover,
    restartToken,
    startFallback,
    streamCursor,
  ]);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      closeSource();
      clearFallback();
      recentSequencesRef.current = [];
      recentSequenceSetRef.current.clear();
    }
  }, [authStatus, clearFallback, closeSource]);

  return { status, reconnect };
}
