"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { AuthApiError, getCurrentUser, signOut } from "./api";
import type { AuthenticationResponse, AuthStatus, AuthUser } from "./types";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  csrfToken: string | null;
  error: string | null;
  setAuthenticatedSession: (response: AuthenticationResponse) => void;
  refreshSession: () => Promise<void>;
  signOut: () => Promise<boolean>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function getSessionRestoreError(): string {
  return "We couldn't check your session. Please try again.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const setAuthenticatedSession = useCallback(
    (response: AuthenticationResponse) => {
      setUser(response.user);
      setCsrfToken(response.csrfToken);
      setError(null);
      setStatus("authenticated");
    },
    [],
  );

  const clearSession = useCallback(() => {
    setUser(null);
    setCsrfToken(null);
    setError(null);
    setStatus("unauthenticated");
  }, []);

  const refreshSession = useCallback(async () => {
    setStatus("loading");
    setError(null);

    try {
      setAuthenticatedSession(await getCurrentUser());
    } catch (requestError) {
      if (requestError instanceof AuthApiError && requestError.status === 401) {
        clearSession();
        return;
      }

      setUser(null);
      setCsrfToken(null);
      setError(getSessionRestoreError());
      setStatus("unauthenticated");
    }
  }, [clearSession, setAuthenticatedSession]);

  const completeSignOut = useCallback(async (): Promise<boolean> => {
    if (!csrfToken) {
      clearSession();
      return true;
    }

    try {
      await signOut(csrfToken);
      clearSession();
      return true;
    } catch (requestError) {
      if (requestError instanceof AuthApiError && requestError.status === 401) {
        clearSession();
        return true;
      }

      setError("We couldn't sign you out. Please try again.");
      return false;
    }
  }, [clearSession, csrfToken]);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      csrfToken,
      error,
      setAuthenticatedSession,
      refreshSession,
      signOut: completeSignOut,
    }),
    [
      completeSignOut,
      csrfToken,
      error,
      refreshSession,
      setAuthenticatedSession,
      status,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }

  return context;
}
