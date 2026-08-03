"use client";

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

function fixedParameterText(preset: SignalPreset): string {
  const threshold = preset.parameters.threshold
    ? ` · Threshold ${preset.parameters.threshold}`
    : "";
  return `${formatTimeframe(preset.timeframe)} · Close price · Period ${preset.parameters.period}${threshold}`;
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
      return "Telegram delivery is unavailable. Review or reconnect the Telegram destination.";
  }
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
  const sectionId = `telegram-delivery-${subscription.id}`;

  return (
    <div
      aria-labelledby={sectionId}
      className="space-y-3 border-t border-zinc-200 pt-4 dark:border-zinc-700"
    >
      <h5 className="font-medium" id={sectionId}>
        Telegram delivery
      </h5>
      <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
        Send future occurrences from this subscription to your connected private
        Telegram chat.
      </p>
      <dl className="space-y-1 text-sm">
        <div className="flex flex-wrap gap-2">
          <dt className="font-medium">Preference:</dt>
          <dd>{enabled ? "On" : "Off"}</dd>
        </div>
        <div className="flex flex-wrap gap-2">
          <dt className="font-medium">Readiness:</dt>
          <dd>{readinessDescription(readiness)}</dd>
        </div>
      </dl>
      {enabled && readiness !== "ready" ? (
        <p className="text-sm text-amber-700 dark:text-amber-300">
          Delivery preference is on, but Telegram is currently unavailable.
        </p>
      ) : null}
      {isConfirming ? (
        <div aria-live="polite" className="space-y-3">
          <p className="text-sm">
            Send future {preset.name} signals for {marketSymbol} to your
            connected Telegram chat?
          </p>
          <div className="flex flex-wrap gap-3">
            <button
              className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700"
              disabled={isPending}
              onClick={onCancelConfirmation}
              type="button"
            >
              Cancel
            </button>
            <button
              aria-busy={isPending}
              className="rounded-lg bg-zinc-900 px-3 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
              disabled={isPending}
              onClick={() => onSetDelivery(true)}
              type="button"
            >
              {isPending ? "Enabling Telegram…" : "Enable Telegram"}
            </button>
          </div>
        </div>
      ) : (
        <button
          aria-busy={isPending}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
          disabled={isPending || (!enabled && !canEnable)}
          onClick={() => {
            if (enabled) {
              onSetDelivery(false);
              return;
            }

            onAskToEnable();
          }}
          type="button"
        >
          {isPending
            ? enabled
              ? "Disabling Telegram…"
              : "Enabling Telegram…"
            : enabled
              ? "Disable Telegram"
              : "Enable Telegram"}
        </button>
      )}
      <p className="text-xs text-zinc-500 dark:text-zinc-400">
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

  return (
    <article className="flex h-full flex-col justify-between gap-5 rounded-xl border border-zinc-200 p-4 dark:border-zinc-700">
      <div className="space-y-2">
        <h4 className="font-semibold">{preset.name}</h4>
        <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
          {preset.description}
        </p>
        <p className="text-sm font-medium">{fixedParameterText(preset)}</p>
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          Confirmed candle-close input only. Parameters and formula are fixed.
        </p>
      </div>
      <div className="space-y-3">
        <SubscriptionControls
          isConfirmingDisable={isConfirmingDisable}
          isPending={isMutationPending}
          onAskToDisable={onAskToDisable}
          onCancelDisable={onCancelDisable}
          onConfirmDisable={onConfirmDisable}
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
        <button
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700"
          onClick={onViewHistory}
          type="button"
        >
          View history
        </button>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          {marketSymbol} · Preset version {preset.version}
        </p>
      </div>
    </article>
  );
}
