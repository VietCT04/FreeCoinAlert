"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import { getSignalFeed } from "./api";
import {
  isSignalAuthenticationError,
  signalErrorMessage,
} from "./errors";
import type {
  SignalFeedEvent,
  SignalInvalidationEvent,
} from "./types";

const LIVE_SIGNAL_HIGHLIGHT_MS = 5_000;
const MAX_HIGHLIGHTED_EVENTS = 2_000;

type UseSignalFeedOptions = {
  authStatus: AuthStatus;
  refreshSession: () => Promise<void>;
  onNewLiveSignal?: (event: SignalFeedEvent) => void;
};

export type SignalFeedState = {
  events: SignalFeedEvent[];
  error: string | null;
  isInitialLoading: boolean;
  isRefreshing: boolean;
  isLoadingMore: boolean;
  isStale: boolean;
  nextCursor: string | null;
  streamCursor: string | null;
  baselineReady: boolean;
  highlightedEventIds: Set<string>;
  announcement: string | null;
  refreshFirstPage: () => Promise<boolean>;
  loadMore: () => Promise<boolean>;
  applyStreamSignal: (event: SignalFeedEvent) => void;
  applyStreamInvalidation: (event: SignalInvalidationEvent) => boolean;
  clear: () => void;
};

function sortEvents(events: Iterable<SignalFeedEvent>): SignalFeedEvent[] {
  return [...events].sort((left, right) => {
    const occurredAt = right.occurredAt.localeCompare(left.occurredAt);
    return occurredAt === 0 ? right.id.localeCompare(left.id) : occurredAt;
  });
}

function addEventToMap(
  eventMap: Map<string, SignalFeedEvent>,
  incoming: SignalFeedEvent[],
): void {
  for (const event of incoming) {
    eventMap.set(event.id, event);
  }
}

export function useSignalFeed({
  authStatus,
  refreshSession,
  onNewLiveSignal,
}: UseSignalFeedOptions): SignalFeedState {
  const [events, setEvents] = useState<SignalFeedEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isStale, setIsStale] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [streamCursor, setStreamCursor] = useState<string | null>(null);
  const [baselineReady, setBaselineReady] = useState(false);
  const [highlightedEventIds, setHighlightedEventIds] = useState<Set<string>>(
    new Set(),
  );
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const eventMapRef = useRef(new Map<string, SignalFeedEvent>());
  const highlightedIdsRef = useRef(new Set<string>());
  const highlightTimersRef = useRef(new Map<string, number>());
  const requestInFlightRef = useRef(false);
  const baselineReadyRef = useRef(false);
  const onNewLiveSignalRef = useRef(onNewLiveSignal);

  useEffect(() => {
    onNewLiveSignalRef.current = onNewLiveSignal;
  }, [onNewLiveSignal]);

  const handleError = useCallback(
    async (requestError: unknown) => {
      if (isSignalAuthenticationError(requestError)) {
        await refreshSession();
      }
      setError(signalErrorMessage(requestError));
      setIsStale(true);
    },
    [refreshSession],
  );

  const replaceEvents = useCallback((incoming: SignalFeedEvent[]) => {
    addEventToMap(eventMapRef.current, incoming);
    setEvents(sortEvents(eventMapRef.current.values()));
  }, []);

  const refreshFirstPage = useCallback(async (): Promise<boolean> => {
    if (authStatus !== "authenticated" || requestInFlightRef.current) {
      return false;
    }

    requestInFlightRef.current = true;
    setIsRefreshing(true);
    setError(null);

    try {
      const response = await getSignalFeed();
      replaceEvents(response.events);
      setNextCursor(response.nextCursor);
      setStreamCursor(response.streamCursor);
      baselineReadyRef.current = true;
      setBaselineReady(true);
      setIsStale(false);
      return true;
    } catch (requestError) {
      await handleError(requestError);
      return false;
    } finally {
      requestInFlightRef.current = false;
      setIsRefreshing(false);
    }
  }, [authStatus, handleError, replaceEvents]);

  const loadMore = useCallback(async (): Promise<boolean> => {
    if (
      authStatus !== "authenticated" ||
      !nextCursor ||
      requestInFlightRef.current
    ) {
      return false;
    }

    requestInFlightRef.current = true;
    setIsLoadingMore(true);
    setError(null);

    try {
      const response = await getSignalFeed({ cursor: nextCursor });
      replaceEvents(response.events);
      setNextCursor(response.nextCursor);
      setIsStale(false);
      return true;
    } catch (requestError) {
      await handleError(requestError);
      return false;
    } finally {
      requestInFlightRef.current = false;
      setIsLoadingMore(false);
    }
  }, [authStatus, handleError, nextCursor, replaceEvents]);

  const markLiveEvent = useCallback((event: SignalFeedEvent) => {
    highlightedIdsRef.current.add(event.id);
    while (highlightedIdsRef.current.size > MAX_HIGHLIGHTED_EVENTS) {
      const oldestId = highlightedIdsRef.current.values().next().value;
      if (!oldestId) {
        break;
      }
      highlightedIdsRef.current.delete(oldestId);
    }
    setHighlightedEventIds(new Set(highlightedIdsRef.current));
    setAnnouncement(`New live signal: ${event.market.symbol} ${event.preset.name}`);

    const existingTimer = highlightTimersRef.current.get(event.id);
    if (existingTimer) {
      window.clearTimeout(existingTimer);
    }
    const timerId = window.setTimeout(() => {
      highlightedIdsRef.current.delete(event.id);
      highlightTimersRef.current.delete(event.id);
      setHighlightedEventIds(new Set(highlightedIdsRef.current));
    }, LIVE_SIGNAL_HIGHLIGHT_MS);
    highlightTimersRef.current.set(event.id, timerId);
    onNewLiveSignalRef.current?.(event);
  }, []);

  const applyStreamSignal = useCallback(
    (event: SignalFeedEvent) => {
      const wasKnown = eventMapRef.current.has(event.id);
      eventMapRef.current.set(event.id, event);
      setEvents(sortEvents(eventMapRef.current.values()));

      if (
        !wasKnown &&
        event.deliveryMode === "live" &&
        event.status === "current" &&
        baselineReadyRef.current
      ) {
        markLiveEvent(event);
      }
    },
    [markLiveEvent],
  );

  const applyStreamInvalidation = useCallback(
    (event: SignalInvalidationEvent): boolean => {
      const existing = eventMapRef.current.get(event.eventId);
      if (!existing) {
        return false;
      }

      eventMapRef.current.set(event.eventId, {
        ...existing,
        status: "invalidated",
        invalidationReason: event.reason,
        deliveryMode: event.deliveryMode,
      });
      setEvents(sortEvents(eventMapRef.current.values()));
      return true;
    },
    [],
  );

  const clearHighlights = useCallback(() => {
    for (const timerId of highlightTimersRef.current.values()) {
      window.clearTimeout(timerId);
    }
    highlightTimersRef.current.clear();
    highlightedIdsRef.current.clear();
    setHighlightedEventIds(new Set());
  }, []);

  const clear = useCallback(() => {
    eventMapRef.current.clear();
    baselineReadyRef.current = false;
    clearHighlights();
    setEvents([]);
    setNextCursor(null);
    setStreamCursor(null);
    setBaselineReady(false);
    setAnnouncement(null);
    setError(null);
    setIsStale(false);
  }, [clearHighlights]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        clearHighlights();
        setAnnouncement(null);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [clearHighlights]);

  useEffect(() => {
    if (authStatus === "authenticated") {
      void refreshFirstPage();
      return;
    }

    clear();
    setIsInitialLoading(false);
    setIsRefreshing(false);
    setIsLoadingMore(false);
  }, [authStatus, clear, refreshFirstPage]);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      return;
    }

    if (streamCursor === null && !baselineReady) {
      setIsInitialLoading(true);
    } else {
      setIsInitialLoading(false);
    }
  }, [authStatus, baselineReady, streamCursor]);

  return {
    events,
    error,
    isInitialLoading,
    isRefreshing,
    isLoadingMore,
    isStale,
    nextCursor,
    streamCursor,
    baselineReady,
    highlightedEventIds,
    announcement,
    refreshFirstPage,
    loadMore,
    applyStreamSignal,
    applyStreamInvalidation,
    clear,
  };
}
