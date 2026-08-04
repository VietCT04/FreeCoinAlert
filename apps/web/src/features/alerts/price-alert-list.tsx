"use client";

import { useState } from "react";

import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
import { EmptyState } from "@/components/empty-state";
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

import type { PriceAlert } from "./types";

type PriceAlertListProps = {
  alerts: PriceAlert[];
  filterLabel: string;
  isLoadingMore: boolean;
  nextCursor: string | null;
  onDelete: (id: string) => Promise<boolean>;
  onLoadMore: () => Promise<void>;
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Unknown time" : date.toLocaleString();
}

function monitoringMessage(alert: PriceAlert): string | null {
  if (alert.status !== "active") return null;
  return alert.evaluationReady
    ? "Monitoring live prices."
    : "Waiting for the first live price before evaluation.";
}

function deliveryMessage(status: PriceAlert["delivery"]["status"]): string {
  return {
    not_queued: "No Telegram message was queued.",
    queued: "Telegram notification queued.",
    sending: "Sending Telegram notification…",
    retrying: "Telegram notification is waiting to retry.",
    sent: "Telegram accepted the notification.",
    failed: "Telegram notification could not be sent.",
    outcome_unknown:
      "We could not confirm whether Telegram accepted the notification. Check Telegram before taking further action.",
  }[status];
}

function marketWarning(alert: PriceAlert): string | null {
  if (alert.marketData.status === "stale") {
    return "Live market data is delayed. Alert evaluation is temporarily paused.";
  }
  if (alert.marketData.status === "disconnected") {
    return "The market-data connection is unavailable. Evaluation will resume after reconnecting.";
  }
  if (alert.marketData.status === "unavailable") {
    return "This market is unavailable. The alert is not being evaluated.";
  }
  return null;
}

function statusReasonMessage(alert: PriceAlert): string | null {
  switch (alert.statusReason) {
    case "market_disabled":
      return "This market is no longer available for the alert.";
    case "evaluation_invariant":
      return "This alert could not be evaluated safely.";
    case "user_disabled":
      return "This alert was disabled.";
    default:
      return alert.statusReason ? "This alert has a status update." : null;
  }
}

export function PriceAlertList({
  alerts,
  filterLabel,
  isLoadingMore,
  nextCursor,
  onDelete,
  onLoadMore,
}: PriceAlertListProps) {
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  if (!alerts.length) {
    return (
      <EmptyState
        description={`Price alerts in the ${filterLabel.toLowerCase()} view will appear here.`}
        title={`No ${filterLabel.toLowerCase()} price alerts`}
      />
    );
  }

  async function confirmDelete(id: string) {
    setDeletingId(id);
    const deleted = await onDelete(id);
    if (deleted) {
      setConfirmingId(null);
    }
    setDeletingId(null);
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        {alerts.map((alert) => {
          const warning = marketWarning(alert);
          const reason = statusReasonMessage(alert);
          const canDelete = alert.status === "active" || alert.status === "disabled";
          const monitoring = monitoringMessage(alert);
          const isDeleting = deletingId === alert.id;

          return (
            <Card aria-busy={isDeleting} key={alert.id}>
              <CardHeader className="gap-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <CardTitle>
                      {alert.market.baseAsset}/{alert.market.quoteAsset}
                    </CardTitle>
                    <CardDescription>
                      {alert.market.symbol} · {alert.market.exchange} {alert.market.marketType}
                    </CardDescription>
                  </div>
                  <StatusBadge status={alert.status} />
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="font-medium">
                  Crosses {alert.direction === "cross_above" ? "above" : "below"}{" "}
                  {alert.targetPrice} {alert.market.quoteAsset}
                </p>
                {monitoring ? <p className="text-sm">{monitoring}</p> : null}
                {alert.lastObservedPrice ? (
                  <p className="text-sm text-muted-foreground">
                    Last observed price: {alert.lastObservedPrice} {alert.market.quoteAsset}
                  </p>
                ) : null}
                <p className="text-sm text-muted-foreground">
                  Created {formatDate(alert.createdAt)}
                </p>
                {alert.trigger ? (
                  <p className="text-sm">
                    Triggered at {alert.trigger.price} {alert.market.quoteAsset} on{" "}
                    {formatDate(alert.trigger.occurredAt)}
                  </p>
                ) : null}
                {reason ? <p className="text-sm text-muted-foreground">{reason}</p> : null}
                {alert.status === "triggered" ? (
                  <p className="text-sm">
                    <span className="font-medium">Telegram delivery:</span>{" "}
                    {deliveryMessage(alert.delivery.status)}
                  </p>
                ) : null}
                {warning ? (
                  <Alert>
                    <AlertTitle>Market-data warning</AlertTitle>
                    <AlertDescription>{warning}</AlertDescription>
                  </Alert>
                ) : null}
                {canDelete ? (
                  <>
                    <Button
                      disabled={isDeleting}
                      onClick={() => setConfirmingId(alert.id)}
                      type="button"
                      variant="destructive"
                    >
                      Delete alert
                    </Button>
                    <ConfirmActionDialog
                      confirmLabel="Delete alert"
                      description="Deleting this alert stops evaluation and cannot be restored."
                      isPending={isDeleting}
                      onConfirm={() => void confirmDelete(alert.id)}
                      onOpenChange={(open) => {
                        if (!open && !isDeleting) {
                          setConfirmingId(null);
                        }
                      }}
                      open={confirmingId === alert.id}
                      title="Delete this price alert?"
                    />
                  </>
                ) : null}
              </CardContent>
            </Card>
          );
        })}
      </div>
      {nextCursor ? (
        <Button
          aria-busy={isLoadingMore}
          disabled={isLoadingMore}
          onClick={() => void onLoadMore()}
          type="button"
          variant="outline"
        >
          {isLoadingMore ? "Loading…" : "Load more"}
        </Button>
      ) : null}
    </div>
  );
}
