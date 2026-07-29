"use client";

import { useState } from "react";

import { useAuth } from "../auth/auth-provider";
import type {
  TelegramConnection,
  TelegramTestNotification,
} from "./types";
import { useTelegramConnection } from "./use-telegram-connection";

function formatDate(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);

  if (Number.isNaN(date.valueOf())) {
    return null;
  }

  return date.toLocaleString();
}

function getConnectionDescription(connection: TelegramConnection): string {
  switch (connection.status) {
    case "linking":
      return "Telegram connection is waiting for confirmation.";
    case "connected":
      return "Telegram is connected.";
    case "degraded":
      return "Telegram needs attention. Disconnect it and create a new connection before notifications can resume.";
    case "not_connected":
    case "disconnected":
      return "Telegram is not connected.";
  }
}

function getNotificationMessage(notification: TelegramTestNotification): string {
  switch (notification.status) {
    case "queued":
      return "Test notification queued.";
    case "sending":
      return "Sending test notification…";
    case "retrying":
      return "Telegram asked us to retry. The notification is still pending.";
    case "sent":
      return "Telegram accepted the test notification.";
    case "failed":
      if (notification.failureCode === "telegram_delivery_outcome_unknown") {
        return "We could not confirm whether Telegram accepted the message. Check Telegram before trying again.";
      }

      if (notification.failureCode === "telegram_not_configured") {
        return "Telegram notifications are not configured right now.";
      }

      if (notification.failureCode === "telegram_connection_degraded") {
        return "Reconnect Telegram before sending another test.";
      }

      return "The test notification could not be sent.";
  }
}

export function TelegramConnectionPanel() {
  const { csrfToken, refreshSession, status } = useAuth();
  const [isConfirmingDisconnect, setIsConfirmingDisconnect] = useState(false);
  const {
    connection,
    connectionError,
    createLink,
    deepLink,
    disconnect,
    isConnecting,
    isConnectionLoading,
    isDisconnecting,
    isLinkExpired,
    isTestNotificationPending,
    notification,
    notificationError,
    notificationPollingExpired,
    queueTestNotification,
    refreshConnection,
    refreshTestNotification,
  } = useTelegramConnection({
    authStatus: status,
    csrfToken,
    refreshSession,
  });

  if (status !== "authenticated") {
    return null;
  }

  if (isConnectionLoading && !connection) {
    return <p aria-live="polite">Checking your Telegram connection…</p>;
  }

  const currentConnection = connection ?? { status: "not_connected" as const };
  const canConnect =
    currentConnection.status === "not_connected" ||
    currentConnection.status === "disconnected" ||
    (currentConnection.status === "linking" && isLinkExpired);
  const canDisconnect =
    currentConnection.status === "connected" || currentConnection.status === "degraded";
  const expiresAt = formatDate(currentConnection.linkExpiresAt);
  const connectedAt = formatDate(currentConnection.connectedAt);
  const lastVerifiedAt = formatDate(currentConnection.lastVerifiedAt);

  async function handleDisconnect() {
    if (await disconnect()) {
      setIsConfirmingDisconnect(false);
    }
  }

  return (
    <section
      aria-labelledby="telegram-connection-heading"
      className="space-y-4 rounded-xl border border-zinc-200 p-5 dark:border-zinc-700"
    >
      <div className="space-y-1">
        <h2 className="text-xl font-semibold" id="telegram-connection-heading">
          Telegram notifications
        </h2>
        <p aria-live="polite" className="text-zinc-600 dark:text-zinc-300">
          {getConnectionDescription(currentConnection)}
        </p>
      </div>

      {currentConnection.status === "linking" ? (
        <div className="space-y-3">
          {expiresAt ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              {isLinkExpired ? "The link expired" : `Link expires ${expiresAt}`}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-3">
            {deepLink ? (
              <a
                className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white dark:bg-zinc-50 dark:text-zinc-900"
                href={deepLink}
                rel="noreferrer"
                target="_blank"
              >
                Open FreeCoinAlert bot in Telegram
              </a>
            ) : null}
            <button
              className="rounded-lg border border-zinc-300 px-4 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
              disabled={isConnectionLoading}
              onClick={() => void refreshConnection()}
              type="button"
            >
              Refresh status
            </button>
            {isLinkExpired ? (
              <button
                className="rounded-lg border border-zinc-300 px-4 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
                disabled={isConnecting}
                onClick={() => void createLink()}
                type="button"
              >
                {isConnecting ? "Creating link…" : "Create new link"}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {canConnect ? (
        <div className="space-y-3">
          <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
            Open the FreeCoinAlert bot in Telegram and press Start to connect it.
          </p>
          <button
            className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
            disabled={isConnecting}
            onClick={() => void createLink()}
            type="button"
          >
            {isConnecting ? "Creating link…" : "Connect Telegram"}
          </button>
        </div>
      ) : null}

      {currentConnection.status === "connected" ? (
        <div className="space-y-3">
          {currentConnection.username ? <p>@{currentConnection.username}</p> : null}
          {connectedAt ? <p className="text-sm">Connected {connectedAt}</p> : null}
          {lastVerifiedAt ? <p className="text-sm">Last verified {lastVerifiedAt}</p> : null}
          <button
            className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
            disabled={isTestNotificationPending}
            onClick={() => void queueTestNotification()}
            type="button"
          >
            {isTestNotificationPending ? "Queueing test notification…" : "Send test notification"}
          </button>
        </div>
      ) : null}

      {notification ? (
        <div aria-live="polite" className="space-y-2">
          <p>{getNotificationMessage(notification)}</p>
          {notificationPollingExpired &&
          notification.status !== "sent" &&
          notification.status !== "failed" ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm text-zinc-600 dark:text-zinc-300">
                Processing is still pending.
              </p>
              <button
                className="rounded-lg border border-zinc-300 px-4 py-2 font-medium dark:border-zinc-700"
                onClick={() => void refreshTestNotification()}
                type="button"
              >
                Refresh test status
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {canDisconnect ? (
        <div className="space-y-3 border-t border-zinc-200 pt-4 dark:border-zinc-700">
          {isConfirmingDisconnect ? (
            <>
              <p>Disconnect Telegram? Future notifications will stop until you connect it again.</p>
              <div className="flex flex-wrap gap-3">
                <button
                  className="rounded-lg border border-zinc-300 px-4 py-2 font-medium dark:border-zinc-700"
                  disabled={isDisconnecting}
                  onClick={() => setIsConfirmingDisconnect(false)}
                  type="button"
                >
                  Cancel
                </button>
                <button
                  className="rounded-lg bg-red-700 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={isDisconnecting}
                  onClick={() => void handleDisconnect()}
                  type="button"
                >
                  {isDisconnecting ? "Disconnecting…" : "Confirm disconnect"}
                </button>
              </div>
            </>
          ) : (
            <button
              className="rounded-lg border border-red-300 px-4 py-2 font-medium text-red-800 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-900 dark:text-red-300"
              disabled={isDisconnecting}
              onClick={() => setIsConfirmingDisconnect(true)}
              type="button"
            >
              Disconnect Telegram
            </button>
          )}
        </div>
      ) : null}

      {connectionError ? (
        <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">
          {connectionError}
        </p>
      ) : null}
      {notificationError ? (
        <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">
          {notificationError}
        </p>
      ) : null}
    </section>
  );
}
