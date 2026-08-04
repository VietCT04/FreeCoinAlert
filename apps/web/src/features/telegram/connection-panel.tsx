"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { StatusBadge } from "@/components/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { useAuth } from "../auth/auth-provider";
import type {
  TelegramConnection,
  TelegramTestNotification,
} from "./types";
import { useTelegramConnection } from "./use-telegram-connection";
import { useTelegramUsageSummary } from "./use-telegram-usage-summary";

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? null : date.toLocaleString();
}

function connectionLabel(status: TelegramConnection["status"]): string {
  switch (status) {
    case "not_connected":
      return "Not connected";
    case "linking":
      return "Linking";
    case "connected":
      return "Connected";
    case "degraded":
      return "Needs attention";
    case "disconnected":
      return "Disconnected";
  }
}

function getConnectionDescription(connection: TelegramConnection): string {
  switch (connection.status) {
    case "linking":
      return "Telegram connection is waiting for confirmation.";
    case "connected":
      return "Telegram is connected to your private destination.";
    case "degraded":
      return "Telegram needs attention before notifications can resume.";
    case "not_connected":
      return "Connect a private Telegram destination to receive notifications.";
    case "disconnected":
      return "Telegram is disconnected. Future notifications remain paused until reconnection.";
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
  const notificationStatusRef = useRef<TelegramTestNotification["status"] | null>(
    null,
  );
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
  const usage = useTelegramUsageSummary({
    authStatus: status,
    refreshSession,
  });

  useEffect(() => {
    const previousStatus = notificationStatusRef.current;
    if (notification?.status === "sent" && previousStatus !== "sent") {
      toast.success("Telegram accepted the test notification.");
    }
    notificationStatusRef.current = notification?.status ?? null;
  }, [notification?.status]);

  if (status !== "authenticated") {
    return null;
  }

  if (isConnectionLoading && !connection) {
    return (
      <div aria-busy="true" aria-label="Checking Telegram connection" role="status">
        <Skeleton className="h-44 w-full" />
      </div>
    );
  }

  const currentConnection = connection ?? { status: "not_connected" as const };
  const canConnect =
    currentConnection.status === "not_connected" ||
    currentConnection.status === "disconnected" ||
    (currentConnection.status === "linking" && isLinkExpired);
  const canDisconnect =
    currentConnection.status === "connected" ||
    currentConnection.status === "degraded";
  const expiresAt = formatDate(currentConnection.linkExpiresAt);
  const connectedAt = formatDate(currentConnection.connectedAt);
  const lastVerifiedAt = formatDate(currentConnection.lastVerifiedAt);

  async function handleCreateLink() {
    if (await createLink()) {
      toast.success("Telegram link created.");
    }
  }

  async function handleDisconnect() {
    if (await disconnect()) {
      setIsConfirmingDisconnect(false);
      toast.success("Telegram disconnected.");
    }
  }

  return (
    <div className="space-y-6" id="telegram-connection">
      <Card>
        <CardHeader className="gap-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <CardTitle>Connection status</CardTitle>
              <CardDescription aria-live="polite">
                {getConnectionDescription(currentConnection)}
              </CardDescription>
            </div>
            <StatusBadge status={connectionLabel(currentConnection.status)} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {currentConnection.username ? <p>@{currentConnection.username}</p> : null}
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            {connectedAt ? (
              <div>
                <dt className="font-medium">Connected</dt>
                <dd className="text-muted-foreground">{connectedAt}</dd>
              </div>
            ) : null}
            {lastVerifiedAt ? (
              <div>
                <dt className="font-medium">Last verified</dt>
                <dd className="text-muted-foreground">{lastVerifiedAt}</dd>
              </div>
            ) : null}
          </dl>
          <div className="flex flex-wrap gap-2">
            <Button
              aria-busy={isConnectionLoading}
              disabled={isConnectionLoading}
              onClick={() => void refreshConnection()}
              type="button"
              variant="outline"
            >
              {isConnectionLoading ? "Refreshing…" : "Refresh status"}
            </Button>
            {currentConnection.status === "connected" ? (
              <Button
                aria-busy={isTestNotificationPending}
                disabled={isTestNotificationPending}
                onClick={() => void queueTestNotification()}
                type="button"
              >
                {isTestNotificationPending
                  ? "Queueing test notification…"
                  : "Send test notification"}
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {canConnect || currentConnection.status === "linking" ? (
        <Card>
          <CardHeader>
            <CardTitle>Connection and linking</CardTitle>
            <CardDescription>
              Link one private Telegram destination for alert and preset-signal notifications.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {currentConnection.status === "linking" ? (
              <>
                <p className="text-sm text-muted-foreground">
                  {isLinkExpired
                    ? "The link expired."
                    : expiresAt
                      ? `Link expires ${expiresAt}.`
                      : "The link is waiting for confirmation."}
                </p>
                <div className="flex flex-wrap gap-2">
                  {deepLink && !isLinkExpired ? (
                    <Button asChild>
                      <a href={deepLink} rel="noreferrer" target="_blank">
                        Open FreeCoinAlert bot in Telegram
                      </a>
                    </Button>
                  ) : null}
                  {isLinkExpired ? (
                    <Button
                      aria-busy={isConnecting}
                      disabled={isConnecting}
                      onClick={() => void handleCreateLink()}
                      type="button"
                    >
                      {isConnecting ? "Creating link…" : "Create new link"}
                    </Button>
                  ) : null}
                  <Button
                    disabled={isConnectionLoading}
                    onClick={() => void refreshConnection()}
                    type="button"
                    variant="outline"
                  >
                    Refresh status
                  </Button>
                </div>
              </>
            ) : (
              <>
                <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
                  <li>Select Connect Telegram.</li>
                  <li>Open the FreeCoinAlert bot in Telegram.</li>
                  <li>Press Start to confirm the private connection.</li>
                </ol>
                <Button
                  aria-busy={isConnecting}
                  disabled={isConnecting}
                  onClick={() => void handleCreateLink()}
                  type="button"
                >
                  {isConnecting ? "Creating link…" : "Connect Telegram"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      ) : null}

      {currentConnection.status === "degraded" ? (
        <Alert>
          <AlertTitle>Telegram needs attention</AlertTitle>
          <AlertDescription>
            Disconnect this destination and create a new connection before notifications can resume.
          </AlertDescription>
        </Alert>
      ) : null}

      {connectionError ? (
        <InlineError
          message={connectionError}
          retryAction={<InlineErrorRetryButton onRetry={() => void refreshConnection()} />}
          title="Telegram connection update failed"
        />
      ) : null}

      {notification ? (
        <Card>
          <CardHeader className="gap-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Test-message result</CardTitle>
                <CardDescription>
                  Provider-processing state does not guarantee device receipt.
                </CardDescription>
              </div>
              <StatusBadge status={notification.status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p aria-live="polite">{getNotificationMessage(notification)}</p>
            {notificationPollingExpired &&
            notification.status !== "sent" &&
            notification.status !== "failed" ? (
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm text-muted-foreground">
                  Processing is still pending.
                </p>
                <Button
                  onClick={() => void refreshTestNotification()}
                  type="button"
                  variant="outline"
                >
                  Refresh test status
                </Button>
              </div>
            ) : null}
            {notificationError ? (
              <InlineError
                message={notificationError}
                retryAction={
                  <InlineErrorRetryButton
                    onRetry={() => void refreshTestNotification()}
                  />
                }
                title="Test notification status failed"
              />
            ) : null}
          </CardContent>
        </Card>
      ) : null}
      {!notification && notificationError ? (
        <InlineError
          message={notificationError}
          retryAction={
            <InlineErrorRetryButton onRetry={() => void queueTestNotification()} />
          }
          title="Test notification could not be queued"
        />
      ) : null}

      <Card>
        <CardHeader className="flex-row items-start justify-between gap-3">
          <div>
            <CardTitle>Notification usage</CardTitle>
            <CardDescription>
              Current active features using this private Telegram destination.
            </CardDescription>
          </div>
          <Button
            aria-busy={usage.isLoading}
            disabled={usage.isLoading}
            onClick={() => void usage.refresh()}
            size="sm"
            type="button"
            variant="outline"
          >
            {usage.isLoading ? "Refreshing…" : "Refresh"}
          </Button>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <dt className="text-sm text-muted-foreground">
                Active price alerts using Telegram
              </dt>
              <dd className="text-2xl font-semibold">
                {usage.isLoading ? (
                  <Skeleton className="h-8 w-16" />
                ) : (
                  usage.activePriceAlerts ?? "Unavailable"
                )}
              </dd>
              {usage.priceAlertsError ? (
                <p className="text-sm text-destructive">{usage.priceAlertsError}</p>
              ) : null}
            </div>
            <div className="space-y-1">
              <dt className="text-sm text-muted-foreground">
                Active preset subscriptions with Telegram enabled
              </dt>
              <dd className="text-2xl font-semibold">
                {usage.isLoading ? (
                  <Skeleton className="h-8 w-16" />
                ) : (
                  usage.activePresetSubscriptions ?? "Unavailable"
                )}
              </dd>
              {usage.presetSubscriptionsError ? (
                <p className="text-sm text-destructive">
                  {usage.presetSubscriptionsError}
                </p>
              ) : null}
            </div>
          </dl>
        </CardContent>
      </Card>

      {canDisconnect ? (
        <Card>
          <CardHeader>
            <CardTitle>Disconnect Telegram</CardTitle>
            <CardDescription>
              Future notifications will stop until you connect Telegram again.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              disabled={isDisconnecting}
              onClick={() => setIsConfirmingDisconnect(true)}
              type="button"
              variant="destructive"
            >
              Disconnect Telegram
            </Button>
            <ConfirmActionDialog
              confirmLabel="Disconnect Telegram"
              description="Future notifications will stop until you connect Telegram again."
              isPending={isDisconnecting}
              onConfirm={() => void handleDisconnect()}
              onOpenChange={(open) => {
                if (!open && !isDisconnecting) {
                  setIsConfirmingDisconnect(false);
                }
              }}
              open={isConfirmingDisconnect}
              title="Disconnect this Telegram destination?"
            />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
