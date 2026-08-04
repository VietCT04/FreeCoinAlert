"use client";

import { StatusBadge } from "@/components/status-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

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
    <Card
      className={
        isHighlighted
          ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30"
          : undefined
      }
    >
      <CardHeader className="gap-2">
        {isHighlighted ? (
          <p className="font-semibold text-emerald-800 dark:text-emerald-300">
            New live signal
          </p>
        ) : null}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>
              {event.market.symbol} · {event.preset.name}
            </CardTitle>
            <CardDescription>
              Binance Spot · {formatTimeframe(event.preset.timeframe)} ·{" "}
              {formatDirection(event.preset.direction)}
            </CardDescription>
          </div>
          <StatusBadge
            status={event.status === "current" ? "Current" : "Invalidated"}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>
          Previous: {leftLabel} {event.comparison.previousLeft} · {rightLabel}{" "}
          {event.comparison.previousRight}
        </p>
        <p>
          Current: {leftLabel} {event.comparison.currentLeft} · {rightLabel}{" "}
          {event.comparison.currentRight}
        </p>
        <p>
          Candle close: {event.candle.closePrice} · Closed{" "}
          {formatSignalDate(event.candle.closeTime)}
        </p>
        <p className="text-muted-foreground">
          Occurred {formatSignalDate(event.occurredAt)}
        </p>
        {event.backfilled ? (
          <p className="text-muted-foreground">Backfilled history</p>
        ) : null}
        {event.deliveryMode === "replay" ? (
          <p className="text-muted-foreground">Replayed after live-feed recovery</p>
        ) : null}
        {event.status === "invalidated" ? (
          <p className="text-destructive">
            Invalidated: {event.invalidationReason ?? "This signal is no longer current."}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
