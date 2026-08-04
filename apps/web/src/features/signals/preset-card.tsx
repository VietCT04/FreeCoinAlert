"use client";

import { ConfirmActionDialog } from "@/components/confirm-action-dialog";
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
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

import { formatTimeframe } from "./format";
import { SubscriptionControls } from "./subscription-controls";
import type {
  SignalPreset,
  SignalSubscription,
  SignalTelegramDeliveryReadiness,
} from "./types";

type PresetCardProps = {
  marketSymbol: string;
  preset: SignalPreset;
  subscription: SignalSubscription | undefined;
  isPending: boolean;
  isConfirmingDisable: boolean;
  isTelegramDeliveryPending: boolean;
  isConfirmingTelegramDelivery: boolean;
  onSubscribe: () => void;
  onAskToDisable: () => void;
  onCancelDisable: () => void;
  onConfirmDisable: () => void;
  onAskToEnableTelegramDelivery: () => void;
  onCancelTelegramDeliveryConfirmation: () => void;
  onSetTelegramDelivery: (enabled: boolean) => void;
  onViewHistory: () => void;
};

function readinessLabel(readiness: SignalTelegramDeliveryReadiness): string {
  switch (readiness) {
    case "ready":
      return "Ready";
    case "linking":
      return "Linking";
    case "not_connected":
      return "Not connected";
    case "degraded":
      return "Needs attention";
  }
}

function readinessDescription(
  readiness: SignalTelegramDeliveryReadiness,
): string {
  switch (readiness) {
    case "ready":
      return "Telegram is connected and available.";
    case "linking":
      return "Finish connecting Telegram before enabling delivery.";
    case "not_connected":
      return "Connect Telegram before enabling delivery.";
    case "degraded":
      return "Telegram delivery is unavailable. Review or reconnect the destination.";
  }
}

function strategyLabel(strategyType: SignalPreset["strategyType"]): string {
  return strategyType === "price_sma_cross" ? "Price/SMA crossing" : "RSI threshold crossing";
}

function TelegramDeliverySection({
  marketSymbol,
  preset,
  subscription,
  isPending,
  isConfirming,
  onAskToEnable,
  onCancelConfirmation,
  onSetDelivery,
}: {
  marketSymbol: string;
  preset: SignalPreset;
  subscription: SignalSubscription;
  isPending: boolean;
  isConfirming: boolean;
  onAskToEnable: () => void;
  onCancelConfirmation: () => void;
  onSetDelivery: (enabled: boolean) => void;
}) {
  const { enabled, readiness } = subscription.telegramDelivery;
  const canEnable = subscription.status === "active" && readiness === "ready";
  const switchId = `telegram-delivery-${subscription.id}`;

  return (
    <div className="space-y-3 border-t pt-4" id={`${switchId}-section`}>
      <div className="space-y-1">
        <h5 className="font-medium">Telegram delivery</h5>
        <p className="text-sm text-muted-foreground">
          Send future occurrences from this subscription to your connected private
          Telegram chat.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Switch
            aria-describedby={`${switchId}-readiness`}
            checked={enabled}
            disabled={
              isPending ||
              subscription.status !== "active" ||
              (!enabled && !canEnable)
            }
            id={switchId}
            onCheckedChange={(checked) => {
              if (checked) {
                onAskToEnable();
                return;
              }
              onSetDelivery(false);
            }}
          />
          <Label htmlFor={switchId}>Delivery preference</Label>
        </div>
        <StatusBadge status={enabled ? "On" : "Off"} />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm" id={`${switchId}-readiness`}>
        <span className="font-medium">Readiness:</span>
        <StatusBadge status={readinessLabel(readiness)} />
        <span className="text-muted-foreground">{readinessDescription(readiness)}</span>
      </div>
      {enabled && readiness !== "ready" ? (
        <Alert>
          <AlertTitle>Telegram needs attention</AlertTitle>
          <AlertDescription>
            Delivery preference is on, but Telegram is currently unavailable.
          </AlertDescription>
        </Alert>
      ) : null}
      <ConfirmActionDialog
        confirmLabel="Enable Telegram"
        confirmVariant="default"
        description={`Send future ${preset.name} signals for ${marketSymbol} to your connected Telegram chat?`}
        isPending={isPending}
        onConfirm={() => onSetDelivery(true)}
        onOpenChange={(open) => {
          if (!open && !isPending) {
            onCancelConfirmation();
          }
        }}
        open={isConfirming}
        title="Enable Telegram delivery?"
      />
      <p className="text-xs text-muted-foreground">
        Website signal history and browser sound are independent from Telegram
        delivery.
      </p>
    </div>
  );
}

export function PresetCard({
  marketSymbol,
  preset,
  subscription,
  isPending,
  isConfirmingDisable,
  isTelegramDeliveryPending,
  isConfirmingTelegramDelivery,
  onSubscribe,
  onAskToDisable,
  onCancelDisable,
  onConfirmDisable,
  onAskToEnableTelegramDelivery,
  onCancelTelegramDeliveryConfirmation,
  onSetTelegramDelivery,
  onViewHistory,
}: PresetCardProps) {
  const subscriptionStatus = subscription?.status ?? "inactive";
  const isMutationPending = isPending || isTelegramDeliveryPending;
  const directionLabel = preset.direction === "cross_above" ? "Crosses above" : "Crosses below";

  return (
    <Card aria-busy={isMutationPending}>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle>{preset.name}</CardTitle>
            <CardDescription>{preset.description}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={formatTimeframe(preset.timeframe)} />
            <StatusBadge status={directionLabel} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Confirmed candle-close input only. Parameters and formula are fixed and
          server-controlled.
        </p>
        <details className="rounded-lg border px-3 py-2 text-sm">
          <summary className="cursor-pointer font-medium">Technical details</summary>
          <dl className="mt-3 grid gap-2 text-muted-foreground sm:grid-cols-2">
            <div>
              <dt className="font-medium text-foreground">Preset code/version</dt>
              <dd>
                {preset.code} v{preset.version}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Strategy type</dt>
              <dd>{strategyLabel(preset.strategyType)}</dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Timeframe</dt>
              <dd>{formatTimeframe(preset.timeframe)}</dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Direction</dt>
              <dd>{directionLabel}</dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Period</dt>
              <dd>{preset.parameters.period}</dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Threshold</dt>
              <dd>{preset.parameters.threshold ?? "Not applicable"}</dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Close-price input</dt>
              <dd>{preset.parameters.priceInput}</dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Definition</dt>
              <dd>Fixed/server-controlled</dd>
            </div>
          </dl>
        </details>

        <SubscriptionControls
          isPending={isMutationPending}
          onAskToDisable={onAskToDisable}
          onSubscribe={onSubscribe}
          status={subscriptionStatus}
        />

        {subscription?.status === "active" ? (
          <TelegramDeliverySection
            isConfirming={isConfirmingTelegramDelivery}
            isPending={isMutationPending}
            marketSymbol={marketSymbol}
            onAskToEnable={onAskToEnableTelegramDelivery}
            onCancelConfirmation={onCancelTelegramDeliveryConfirmation}
            onSetDelivery={onSetTelegramDelivery}
            preset={preset}
            subscription={subscription}
          />
        ) : null}

        <Button
          disabled={isMutationPending}
          onClick={onViewHistory}
          type="button"
          variant="outline"
        >
          View history
        </Button>
        <p className="text-xs text-muted-foreground">
          {marketSymbol} · Preset version {preset.version}
        </p>

        <ConfirmActionDialog
          confirmLabel="Disable signal"
          description={
            "Disabling this subscription stops new live events for this market and preset. " +
            "Its history remains available."
          }
          isPending={isMutationPending}
          onConfirm={onConfirmDisable}
          onOpenChange={(open) => {
            if (!open && !isMutationPending) {
              onCancelDisable();
            }
          }}
          open={isConfirmingDisable}
          title="Disable this signal subscription?"
        />
      </CardContent>
    </Card>
  );
}
