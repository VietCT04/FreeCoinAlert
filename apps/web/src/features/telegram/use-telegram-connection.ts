"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import type { AuthStatus } from "../auth/types";
import {
  createTelegramLink,
  disconnectTelegram,
  getTelegramConnection,
  getTelegramTestNotification,
  queueTelegramTestNotification,
  TelegramApiError,
} from "./api";
import type {
  TelegramConnection,
  TelegramTestNotification,
} from "./types";

const CONNECTION_POLL_INTERVAL_MS = 2_000;
const CONNECTION_POLL_MAX_MS = 10 * 60 * 1_000;
const TEST_NOTIFICATION_POLL_MAX_MS = 60 * 1_000;
const TEST_NOTIFICATION_POLL_INTERVAL_MS = 2_000;

type UseTelegramConnectionOptions = {
  authStatus: AuthStatus;
  csrfToken: string | null;
  refreshSession: () => Promise<void>;
};

export type TelegramConnectionState = {
  connection: TelegramConnection | null;
  connectionError: string | null;
  deepLink: string | null;
  isConnectionLoading: boolean;
  isConnecting: boolean;
  isDisconnecting: boolean;
  isLinkExpired: boolean;
  isTestNotificationPending: boolean;
  notification: TelegramTestNotification | null;
  notificationError: string | null;
  notificationPollingExpired: boolean;
  refreshConnection: () => Promise<void>;
  createLink: () => Promise<boolean>;
  queueTestNotification: () => Promise<boolean>;
  refreshTestNotification: () => Promise<void>;
  disconnect: () => Promise<boolean>;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof TelegramApiError) {
    const rateLimitSuffix = error.retryAfter
      ? ` Try again in ${error.retryAfter} seconds.`
      : "";

    switch (error.code) {
      case "TELEGRAM_NOT_CONFIGURED":
        return "Telegram notifications are not configured right now.";
      case "TELEGRAM_ALREADY_CONNECTED":
        return "Telegram is already connected to this account.";
      case "TELEGRAM_LINK_RATE_LIMITED":
        return `Too many Telegram link requests.${rateLimitSuffix}`;
      case "TELEGRAM_LINK_UNAVAILABLE":
        return "A Telegram connection link is unavailable right now. Please try again.";
      case "TELEGRAM_NOT_CONNECTED":
        return "Connect Telegram before requesting a test notification.";
      case "TELEGRAM_CONNECTION_DEGRADED":
        return "Reconnect Telegram before sending another test.";
      case "TELEGRAM_TEST_RATE_LIMITED":
        return `Too many test notification requests.${rateLimitSuffix}`;
      case "TELEGRAM_NOTIFICATION_NOT_FOUND":
        return "The test notification is no longer available. Start a new test if needed.";
      case "TELEGRAM_NOTIFICATION_UNAVAILABLE":
        return "The test notification is unavailable right now. Please try again.";
      case "AUTHENTICATION_REQUIRED":
        return "Your session has ended. Please sign in again.";
      case "AUTH_CSRF_INVALID":
        return "Your session could not be confirmed. Please refresh and try again.";
      default:
        break;
    }
  }

  return "We couldn't complete that Telegram request. Please try again.";
}

function isAuthenticationError(error: unknown): boolean {
  return (
    error instanceof TelegramApiError &&
    (error.status === 401 || error.code === "AUTHENTICATION_REQUIRED")
  );
}

function isTerminalConnectionStatus(status: TelegramConnection["status"]): boolean {
  return status === "connected" || status === "degraded" || status === "disconnected";
}

function isTerminalNotificationStatus(
  status: TelegramTestNotification["status"],
): boolean {
  return status === "sent" || status === "failed";
}

function hasExpired(linkExpiresAt: string | null | undefined): boolean {
  return Boolean(linkExpiresAt && Date.parse(linkExpiresAt) <= Date.now());
}

function clearTelegramState(
  setConnection: Dispatch<SetStateAction<TelegramConnection | null>>,
  setDeepLink: Dispatch<SetStateAction<string | null>>,
  setNotification: Dispatch<SetStateAction<TelegramTestNotification | null>>,
  setConnectionError: Dispatch<SetStateAction<string | null>>,
  setNotificationError: Dispatch<SetStateAction<string | null>>,
) {
  setConnection(null);
  setDeepLink(null);
  setNotification(null);
  setConnectionError(null);
  setNotificationError(null);
}

export function useTelegramConnection({
  authStatus,
  csrfToken,
  refreshSession,
}: UseTelegramConnectionOptions): TelegramConnectionState {
  const [connection, setConnection] = useState<TelegramConnection | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [isConnectionLoading, setIsConnectionLoading] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [isLinkExpired, setIsLinkExpired] = useState(false);
  const [isTestNotificationPending, setIsTestNotificationPending] = useState(false);
  const [notification, setNotification] = useState<TelegramTestNotification | null>(null);
  const [notificationError, setNotificationError] = useState<string | null>(null);
  const [notificationPollingExpired, setNotificationPollingExpired] = useState(false);
  const connectionRequestInFlight = useRef(false);
  const notificationRequestInFlight = useRef(false);
  const linkingStartedAt = useRef<number | null>(null);
  const notificationPollingStartedAt = useRef<number | null>(null);
  const testIdempotencyKey = useRef<string | null>(null);
  const updateConnection = useCallback((next: TelegramConnection) => {
    setConnection(next);
  }, []);

  const handleRequestError = useCallback(
    async (
      error: unknown,
      setError: Dispatch<SetStateAction<string | null>>,
    ) => {
      if (isAuthenticationError(error)) {
        await refreshSession();
      }

      setError(getErrorMessage(error));
    },
    [refreshSession],
  );

  const refreshConnection = useCallback(async () => {
    if (authStatus !== "authenticated" || connectionRequestInFlight.current) {
      return;
    }

    connectionRequestInFlight.current = true;
    setIsConnectionLoading(true);
    setConnectionError(null);

    try {
      const response = await getTelegramConnection();
      updateConnection(response.connection);

      if (isTerminalConnectionStatus(response.connection.status)) {
        setDeepLink(null);
      }

      setIsLinkExpired(hasExpired(response.connection.linkExpiresAt));
    } catch (error) {
      await handleRequestError(error, setConnectionError);
    } finally {
      connectionRequestInFlight.current = false;
      setIsConnectionLoading(false);
    }
  }, [authStatus, handleRequestError, updateConnection]);

  const refreshTestNotification = useCallback(async () => {
    if (!notification || notificationRequestInFlight.current) {
      return;
    }

    notificationRequestInFlight.current = true;
    setNotificationError(null);

    try {
      const response = await getTelegramTestNotification(notification.id);
      setNotification(response.notification);
    } catch (error) {
      await handleRequestError(error, setNotificationError);
    } finally {
      notificationRequestInFlight.current = false;
    }
  }, [handleRequestError, notification]);

  const createLink = useCallback(async (): Promise<boolean> => {
    if (!csrfToken || isConnecting) {
      return false;
    }

    setIsConnecting(true);
    setConnectionError(null);

    try {
      const response = await createTelegramLink(csrfToken);
      linkingStartedAt.current = Date.now();
      updateConnection(response.connection);
      setDeepLink(response.telegramUrl);
      setIsLinkExpired(hasExpired(response.connection.linkExpiresAt));
      window.open(response.telegramUrl, "_blank", "noopener,noreferrer");
      return true;
    } catch (error) {
      await handleRequestError(error, setConnectionError);
      return false;
    } finally {
      setIsConnecting(false);
    }
  }, [csrfToken, handleRequestError, isConnecting, updateConnection]);

  const queueTestNotification = useCallback(async (): Promise<boolean> => {
    if (!csrfToken || isTestNotificationPending) {
      return false;
    }

    setIsTestNotificationPending(true);
    setNotificationError(null);
    const idempotencyKey = testIdempotencyKey.current ?? crypto.randomUUID();
    testIdempotencyKey.current = idempotencyKey;

    try {
      const response = await queueTelegramTestNotification(csrfToken, idempotencyKey);
      testIdempotencyKey.current = null;
      notificationPollingStartedAt.current = Date.now();
      setNotificationPollingExpired(false);
      setNotification(response.notification);
      return true;
    } catch (error) {
      await handleRequestError(error, setNotificationError);
      return false;
    } finally {
      setIsTestNotificationPending(false);
    }
  }, [csrfToken, handleRequestError, isTestNotificationPending]);

  const disconnect = useCallback(async () => {
    if (!csrfToken || isDisconnecting) {
      return false;
    }

    setIsDisconnecting(true);
    setConnectionError(null);

    try {
      await disconnectTelegram(csrfToken);
      linkingStartedAt.current = null;
      notificationPollingStartedAt.current = null;
      testIdempotencyKey.current = null;
      updateConnection({ status: "disconnected" });
      setDeepLink(null);
      setNotification(null);
      setNotificationError(null);
      setNotificationPollingExpired(false);
      return true;
    } catch (error) {
      await handleRequestError(error, setConnectionError);
      return false;
    } finally {
      setIsDisconnecting(false);
    }
  }, [csrfToken, handleRequestError, isDisconnecting, updateConnection]);

  useEffect(() => {
    if (authStatus === "authenticated") {
      void refreshConnection();
      return;
    }

    linkingStartedAt.current = null;
    notificationPollingStartedAt.current = null;
    testIdempotencyKey.current = null;
    clearTelegramState(
      setConnection,
      setDeepLink,
      setNotification,
      setConnectionError,
      setNotificationError,
    );
    setIsLinkExpired(false);
    setNotificationPollingExpired(false);
  }, [authStatus, refreshConnection]);

  useEffect(() => {
    if (connection?.status !== "linking" || isLinkExpired) {
      return;
    }

    if (linkingStartedAt.current === null) {
      linkingStartedAt.current = Date.now();
    }

    const pollConnection = () => {
      const linkHasExpired = hasExpired(connection.linkExpiresAt);
      const maximumPollingReached =
        linkingStartedAt.current !== null &&
        Date.now() - linkingStartedAt.current >= CONNECTION_POLL_MAX_MS;

      if (linkHasExpired || maximumPollingReached) {
        setIsLinkExpired(linkHasExpired);
        setDeepLink(null);
        return;
      }

      if (!document.hidden) {
        void refreshConnection();
      }
    };

    const intervalId = window.setInterval(pollConnection, CONNECTION_POLL_INTERVAL_MS);
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        pollConnection();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleVisibilityChange);
    };
  }, [connection, isLinkExpired, refreshConnection]);

  useEffect(() => {
    if (
      !notification ||
      isTerminalNotificationStatus(notification.status) ||
      notificationPollingExpired
    ) {
      return;
    }

    if (notificationPollingStartedAt.current === null) {
      notificationPollingStartedAt.current = Date.now();
    }

    const pollNotification = () => {
      const maximumPollingReached =
        notificationPollingStartedAt.current !== null &&
        Date.now() - notificationPollingStartedAt.current >=
          TEST_NOTIFICATION_POLL_MAX_MS;

      if (maximumPollingReached) {
        setNotificationPollingExpired(true);
        return;
      }

      if (!document.hidden) {
        void refreshTestNotification();
      }
    };

    const intervalId = window.setInterval(
      pollNotification,
      TEST_NOTIFICATION_POLL_INTERVAL_MS,
    );
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        pollNotification();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleVisibilityChange);
    };
  }, [notification, notificationPollingExpired, refreshTestNotification]);

  return {
    connection,
    connectionError,
    deepLink,
    isConnectionLoading,
    isConnecting,
    isDisconnecting,
    isLinkExpired,
    isTestNotificationPending,
    notification,
    notificationError,
    notificationPollingExpired,
    refreshConnection,
    createLink,
    queueTestNotification,
    refreshTestNotification,
    disconnect,
  };
}
