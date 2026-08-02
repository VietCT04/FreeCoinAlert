"use client";

import { formatTimeframe } from "./format";
import { SubscriptionControls } from "./subscription-controls";
import type { SignalPreset, SignalSubscription } from "./types";

type PresetCardProps = {
  marketSymbol: string;
  preset: SignalPreset;
  subscription: SignalSubscription | undefined;
  isPending: boolean;
  isConfirmingDisable: boolean;
  onSubscribe: () => void;
  onAskToDisable: () => void;
  onCancelDisable: () => void;
  onConfirmDisable: () => void;
  onViewHistory: () => void;
};

function fixedParameterText(preset: SignalPreset): string {
  const threshold = preset.parameters.threshold
    ? ` · Threshold ${preset.parameters.threshold}`
    : "";
  return `${formatTimeframe(preset.timeframe)} · Close price · Period ${preset.parameters.period}${threshold}`;
}

export function PresetCard({
  marketSymbol,
  preset,
  subscription,
  isPending,
  isConfirmingDisable,
  onSubscribe,
  onAskToDisable,
  onCancelDisable,
  onConfirmDisable,
  onViewHistory,
}: PresetCardProps) {
  const subscriptionStatus = subscription?.status ?? "inactive";

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
          isPending={isPending}
          onAskToDisable={onAskToDisable}
          onCancelDisable={onCancelDisable}
          onConfirmDisable={onConfirmDisable}
          onSubscribe={onSubscribe}
          status={subscriptionStatus}
        />
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
