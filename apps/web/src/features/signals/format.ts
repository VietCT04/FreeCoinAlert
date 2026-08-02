import type {
  SignalDirection,
  SignalTimeframe,
} from "./types";

export function formatTimeframe(timeframe: SignalTimeframe): string {
  return timeframe === "1h" ? "1 hour" : "4 hours";
}

export function formatDirection(direction: SignalDirection): string {
  return direction === "cross_above" ? "crossed above" : "crossed below";
}

export function formatSignalDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "Unknown time"
    : date.toLocaleString(undefined, {
        timeZone: "UTC",
        timeZoneName: "short",
      });
}

export function formatComparisonLabel(label: string): string {
  if (label === "price") {
    return "Close";
  }
  if (label === "sma_200") {
    return "SMA 200";
  }
  if (label === "threshold") {
    return "Threshold";
  }
  if (label.startsWith("rsi_")) {
    return `RSI ${label.slice(4)}`;
  }
  return label;
}
