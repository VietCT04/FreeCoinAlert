"use client";

import {
  formatComparisonLabel,
  formatDirection,
  formatSignalDate,
  formatTimeframe,
} from "./format";
import type { SignalFeedEvent } from "./types";

type SignalFeedEntryProps = {
  event: SignalFeedEvent;
  isHighlighted: boolean;
};

export function SignalFeedEntry({
  event,
  isHighlighted,
}: SignalFeedEntryProps) {
  const leftLabel = formatComparisonLabel(event.comparison.leftLabel);
  const rightLabel = formatComparisonLabel(event.comparison.rightLabel);

  return (
    <article
      className={`space-y-2 rounded-xl border p-4 ${
        isHighlighted
          ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30"
          : "border-zinc-200 dark:border-zinc-700"
      }`}
    >
      {isHighlighted ? (
        <p className="font-semibold text-emerald-800 dark:text-emerald-300">
          New live signal
        </p>
      ) : null}
      <h4 className="font-semibold">
        {event.market.symbol} · Binance Spot
      </h4>
      <p>
        {event.preset.name} · {formatTimeframe(event.preset.timeframe)}
      </p>
      <p className="text-sm">Direction: {formatDirection(event.preset.direction)}</p>
      <p className="text-sm">
        Previous: {leftLabel} {event.comparison.previousLeft} · {rightLabel}{" "}
        {event.comparison.previousRight}
      </p>
      <p className="text-sm">
        Current: {leftLabel} {event.comparison.currentLeft} · {rightLabel}{" "}
        {event.comparison.currentRight}
      </p>
      <p className="text-sm text-zinc-600 dark:text-zinc-300">
        Candle closed {formatSignalDate(event.candle.closeTime)}
      </p>
      {event.backfilled ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          Historical calculation
        </p>
      ) : null}
      {event.status === "invalidated" ? (
        <p className="text-sm text-red-700 dark:text-red-300">
          Invalidated: {event.invalidationReason ?? "This signal is no longer current."}
        </p>
      ) : (
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          Signal status: current
        </p>
      )}
    </article>
  );
}
