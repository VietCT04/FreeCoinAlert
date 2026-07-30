"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AuthStatus } from "../auth/types";
import { getSupportedMarkets } from "./api";
import type { SupportedMarket } from "./types";

export type MarketsState = {
  error: string | null;
  isLoading: boolean;
  markets: SupportedMarket[];
  refreshMarkets: () => Promise<void>;
};

export function useMarkets(authStatus: AuthStatus): MarketsState {
  const [markets, setMarkets] = useState<SupportedMarket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const requestInFlight = useRef(false);

  const refreshMarkets = useCallback(async () => {
    if (authStatus !== "authenticated" || requestInFlight.current) {
      return;
    }

    requestInFlight.current = true;
    setIsLoading(true);
    setError(null);

    try {
      const response = await getSupportedMarkets();
      setMarkets(response.markets);
    } catch {
      setError("Supported market information is unavailable right now. Please try again.");
    } finally {
      requestInFlight.current = false;
      setIsLoading(false);
    }
  }, [authStatus]);

  useEffect(() => {
    if (authStatus === "authenticated") {
      void refreshMarkets();
      return;
    }

    setMarkets([]);
    setError(null);
    setIsLoading(false);
  }, [authStatus, refreshMarkets]);

  return { error, isLoading, markets, refreshMarkets };
}
