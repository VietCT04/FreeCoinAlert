"use client";

import Link from "next/link";

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

import { useAuth } from "../auth/auth-provider";
import { formatStrategyEntry, formatTimeframe } from "./format";
import type {
  HistoricalAnalysisReport,
  HistoricalAnalysisStatus,
} from "./types";
import { useMonitorEntry } from "./use-monitor-entry";

type MonitorEntryCardProps = {
  report: HistoricalAnalysisReport;
  runStatus: HistoricalAnalysisStatus;
};

function readinessMessage(
  readiness: "ready" | "linking" | "not_connected" | "degraded",
): string {
  switch (readiness) {
    case "linking":
      return "Telegram linking is in progress. Finish connecting Telegram to receive push alerts.";
    case "not_connected":
      return "Connect Telegram to receive push alerts for future entry signals.";
    case "degraded":
      return "Telegram needs attention before push alerts can be enabled.";
    case "ready":
      return "Telegram is ready for push alerts.";
  }
}

export function MonitorEntryCard({
  report,
  runStatus,
}: MonitorEntryCardProps) {
  const { csrfToken, refreshSession, status } = useAuth();
  const monitor = useMonitorEntry({
    authStatus: status,
    csrfToken,
    refreshSession,
    report,
    runStatus,
  });
  const subscription = monitor.subscription;
  const isActive = subscription?.status === "active";
  const isDisabled = subscription?.status === "disabled";
  const telegram = subscription?.telegramDelivery;
  const entry = formatStrategyEntry(report.preset);
  const timeframe = formatTimeframe(report.preset.timeframe);

  return (
    <Card
      aria-busy={
        monitor.isLoading || monitor.isMonitorPending || monitor.isTelegramPending
      }
    >
      <CardHeader>
        <CardTitle>Monitor this entry</CardTitle>
        <CardDescription>
          Follow this entry condition when it occurs again. This is not a live
          position or trading action.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border bg-muted/20 p-3">
          <p className="font-medium">
            {report.market.symbol} · {timeframe}
          </p>
          <p className="text-sm text-muted-foreground">{entry}</p>
        </div>
        <p className="text-sm text-muted-foreground">
          Your historical TP, SL, RSI exit, maximum holding period, hypothetical
          position, and PnL are not live-tracked by this alert.
        </p>

        {monitor.error ? (
          <div className="space-y-2">
            <InlineError
              message={monitor.error}
              retryAction={
                <InlineErrorRetryButton onRetry={() => void monitor.refresh()} />
              }
              title="Entry monitoring request failed"
            />
            {monitor.errorCode === "SIGNAL_SUBSCRIPTION_LIMIT_REACHED" ? (
              <p className="text-sm text-muted-foreground">
                Manage existing subscriptions in{" "}
                <Link className="underline underline-offset-4" href="/preset-signals">
                  Preset Signals
                </Link>
                .
              </p>
            ) : null}
          </div>
        ) : null}

        {monitor.isLoading ? (
          <p aria-live="polite" className="text-sm text-muted-foreground">
            Checking entry-monitoring availability…
          </p>
        ) : null}

        {!monitor.isLoading && !monitor.error && !monitor.activePreset ? (
          <Alert>
            <AlertTitle>Entry monitoring unavailable</AlertTitle>
            <AlertDescription>
              This historical entry preset is no longer available for new live
              monitoring. Review the currently supported presets in{" "}
              <Link className="underline underline-offset-4" href="/preset-signals">
                Preset Signals
              </Link>
              .
            </AlertDescription>
          </Alert>
        ) : null}

        {!monitor.isLoading && monitor.activePreset && !subscription ? (
          <Button
            disabled={monitor.isMonitorPending}
            onClick={monitor.askToMonitor}
            type="button"
          >
            {monitor.isMonitorPending
              ? "Starting monitoring…"
              : "Monitor this entry"}
          </Button>
        ) : null}

        {isDisabled ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <p className="font-medium">Entry monitoring is off</p>
              <p className="text-sm text-muted-foreground">
                Re-enable the same market and exact preset version.
              </p>
            </div>
            <Button
              disabled={monitor.isMonitorPending}
              onClick={monitor.askToMonitor}
              type="button"
            >
              {monitor.isMonitorPending
                ? "Reactivating…"
                : "Reactivate entry monitoring"}
            </Button>
          </div>
        ) : null}

        {isActive && telegram ? (
          <div className="space-y-3 rounded-lg border p-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium">Entry monitoring is active</p>
                <p className="text-sm text-muted-foreground">
                  Only the entry signal is monitored.
                </p>
              </div>
              <StatusBadge status="Active" />
            </div>

            {telegram.enabled ? (
              <div className="space-y-2">
                <p className="text-sm font-medium">Telegram alerts enabled</p>
                {telegram.readiness !== "ready" ? (
                  <Alert variant="warning">
                    <AlertTitle>Telegram needs attention</AlertTitle>
                    <AlertDescription>
                      {readinessMessage(telegram.readiness)}{" "}
                      <Link className="underline underline-offset-4" href="/telegram">
                        Open Telegram settings
                      </Link>
                      .
                    </AlertDescription>
                  </Alert>
                ) : null}
              </div>
            ) : telegram.readiness === "ready" ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">Telegram delivery is off</p>
                  <p className="text-sm text-muted-foreground">
                    Enable it separately for future entry signals.
                  </p>
                </div>
                <Button
                  disabled={monitor.isTelegramPending}
                  onClick={monitor.askToEnableTelegram}
                  type="button"
                >
                  Enable Telegram alerts
                </Button>
              </div>
            ) : (
              <Alert>
                <AlertTitle>Telegram delivery is not ready</AlertTitle>
                <AlertDescription>
                  {readinessMessage(telegram.readiness)}{" "}
                  <Link className="underline underline-offset-4" href="/telegram">
                    Open Telegram settings
                  </Link>
                  .
                </AlertDescription>
              </Alert>
            )}
          </div>
        ) : null}

        {isActive ? (
          <Button asChild type="button" variant="outline">
            <Link href="/preset-signals">Manage in Preset Signals</Link>
          </Button>
        ) : null}

        <ConfirmActionDialog
          confirmLabel="Start monitoring"
          confirmVariant="default"
          description={`${report.market.symbol} · ${timeframe}. ${entry}. This creates or re-enables a live signal subscription for the entry condition only. It does not track the backtest's TP, SL, maximum holding period, hypothetical position, or PnL.`}
          isPending={monitor.isMonitorPending}
          onConfirm={() => void monitor.startMonitoring()}
          onOpenChange={(open) => {
            if (!open && !monitor.isMonitorPending) {
              monitor.cancelMonitorConfirmation();
            }
          }}
          open={monitor.monitorConfirmationOpen}
          title="Monitor entry signal"
        />
        <ConfirmActionDialog
          confirmLabel="Enable Telegram alerts"
          confirmVariant="default"
          description={`Enable Telegram delivery for future ${entry} signals on ${report.market.symbol} ${timeframe}? This affects entry-signal notifications only; it does not track historical exits, positions, or PnL.`}
          isPending={monitor.isTelegramPending}
          onConfirm={() => void monitor.enableTelegram()}
          onOpenChange={(open) => {
            if (!open && !monitor.isTelegramPending) {
              monitor.cancelTelegramConfirmation();
            }
          }}
          open={monitor.telegramConfirmationOpen}
          title="Enable Telegram alerts?"
        />
      </CardContent>
    </Card>
  );
}
