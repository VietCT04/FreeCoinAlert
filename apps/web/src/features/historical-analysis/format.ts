import type {
  HistoricalAnalysisEquityPoint,
  HistoricalAnalysisStatus,
  HistoricalAnalysisTrade,
} from "./types";

const UTC_DAY_MS = 24 * 60 * 60 * 1000;

export function formatUtcDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Unknown UTC time";
  }

  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return "Unknown UTC time";
  }

  return date.toLocaleString(undefined, {
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

export function formatUtcDateInput(value: Date): string {
  return [value.getUTCFullYear(), value.getUTCMonth() + 1, value.getUTCDate()]
    .map((part, index) => (index === 0 ? String(part) : String(part).padStart(2, "0")))
    .join("-");
}

export function getDefaultUtcDateRange(
  minimumRangeDays: number,
  maximumRangeDays: number,
): { startDate: string; endDate: string } {
  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);
  const lastCompleteDay = new Date(today.getTime() - UTC_DAY_MS);
  const rangeDays = Math.min(Math.max(30, minimumRangeDays), maximumRangeDays);
  const start = new Date(
    lastCompleteDay.getTime() - (rangeDays - 1) * UTC_DAY_MS,
  );

  return {
    startDate: formatUtcDateInput(start),
    endDate: formatUtcDateInput(lastCompleteDay),
  };
}

export function dateInputToUtcBoundary(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return null;
  }

  const date = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(date.valueOf()) || formatUtcDateInput(date) !== value) {
    return null;
  }

  return date.toISOString().replace(".000Z", "Z");
}

export function inclusiveDateRangeToApiRange(
  startDate: string,
  endDate: string,
): { analysisStart: string; analysisEnd: string } | null {
  const analysisStart = dateInputToUtcBoundary(startDate);
  const inclusiveEnd = dateInputToUtcBoundary(endDate);
  if (!analysisStart || !inclusiveEnd) {
    return null;
  }

  const end = new Date(inclusiveEnd);
  end.setUTCDate(end.getUTCDate() + 1);
  return {
    analysisStart,
    analysisEnd: end.toISOString().replace(".000Z", "Z"),
  };
}

export function inclusiveRangeDays(
  startDate: string,
  endDate: string,
): number | null {
  const range = inclusiveDateRangeToApiRange(startDate, endDate);
  if (!range) {
    return null;
  }

  return Math.round(
    (Date.parse(range.analysisEnd) - Date.parse(range.analysisStart)) /
      UTC_DAY_MS,
  );
}

export function formatStatus(
  status: HistoricalAnalysisStatus,
  progressStage: string,
  cancellationRequested: boolean,
): string {
  if ((status === "queued" || status === "running") && cancellationRequested) {
    return "Cancellation requested";
  }
  if (status === "queued") {
    return "Queued";
  }
  if (status === "succeeded") {
    return "Completed";
  }
  if (status === "failed") {
    return "Failed";
  }
  if (status === "cancelled") {
    return "Cancelled";
  }

  switch (progressStage) {
    case "preparing_dataset":
      return "Preparing historical data";
    case "validating_dataset":
      return "Validating historical data";
    case "simulating":
      return "Simulating";
    case "persisting_report":
      return "Saving report";
    default:
      return "Running";
  }
}

export function formatTimeframe(timeframe: string): string {
  if (timeframe === "1h") {
    return "1 hour";
  }
  if (timeframe === "4h") {
    return "4 hours";
  }
  return timeframe;
}

export function formatDirection(direction: string): string {
  if (direction === "cross_above") {
    return "Cross above";
  }
  if (direction === "cross_below") {
    return "Cross below";
  }
  return direction;
}

export function formatStrategyType(strategyType: string): string {
  if (strategyType === "price_sma_cross") {
    return "Price / SMA cross";
  }
  if (strategyType === "rsi_threshold_cross") {
    return "RSI threshold cross";
  }
  return strategyType;
}

export function formatPositionState(positionState: string): string {
  if (positionState === "synthetic_short") {
    return "Synthetic short (analytical inverse exposure)";
  }
  if (positionState === "long") {
    return "Long";
  }
  return "Flat";
}

export function formatOutcome(outcome: string): string {
  if (outcome === "win") {
    return "Win";
  }
  if (outcome === "loss") {
    return "Loss";
  }
  if (outcome === "flat") {
    return "Flat";
  }
  return outcome;
}

function validDecimal(value: string): boolean {
  return /^[-+]?\d+(?:\.\d+)?$/.test(value);
}

function normalizeDecimal(value: string): string | null {
  if (!validDecimal(value)) {
    return null;
  }

  const sign = value.startsWith("-") ? "-" : "";
  const unsigned = value.replace(/^[-+]/, "");
  const [integerPart, fractionPart = ""] = unsigned.split(".");
  const integer = integerPart.replace(/^0+(?=\d)/, "") || "0";
  const fraction = fractionPart.replace(/0+$/, "");
  const normalized = fraction ? `${integer}.${fraction}` : integer;
  return normalized === "0" ? "0" : `${sign}${normalized}`;
}

function roundDecimal(value: string, maximumFractionDigits: number): string | null {
  const normalized = normalizeDecimal(value);
  if (!normalized) {
    return null;
  }

  const sign = normalized.startsWith("-") ? "-" : "";
  const unsigned = normalized.replace(/^-/, "");
  const [integerPart, fractionPart = ""] = unsigned.split(".");
  if (fractionPart.length <= maximumFractionDigits) {
    return `${sign}${unsigned}`;
  }

  const kept = fractionPart.slice(0, maximumFractionDigits);
  const nextDigit = fractionPart[maximumFractionDigits];
  let digits = `${integerPart}${kept}`.split("").map(Number);
  if (nextDigit >= "5") {
    for (let index = digits.length - 1; index >= 0; index -= 1) {
      if (digits[index] < 9) {
        digits[index] += 1;
        break;
      }
      digits[index] = 0;
      if (index === 0) {
        digits.unshift(1);
      }
    }
  }

  const roundedDigits = digits.join("");
  const splitAt = roundedDigits.length - maximumFractionDigits;
  const roundedInteger = roundedDigits.slice(0, splitAt) || "0";
  const roundedFraction = roundedDigits.slice(splitAt).replace(/0+$/, "");
  const result = roundedFraction
    ? `${roundedInteger}.${roundedFraction}`
    : roundedInteger;
  return result === "0" ? "0" : `${sign}${result}`;
}

function shiftDecimal(value: string, places: number): string | null {
  const normalized = normalizeDecimal(value);
  if (!normalized) {
    return null;
  }

  const sign = normalized.startsWith("-") ? "-" : "";
  const unsigned = normalized.replace(/^-/, "");
  const [integerPart, fractionPart = ""] = unsigned.split(".");
  const digits = `${integerPart}${fractionPart}`;
  const decimalIndex = integerPart.length + places;
  let shifted: string;
  if (decimalIndex <= 0) {
    shifted = `0.${"0".repeat(-decimalIndex)}${digits}`;
  } else if (decimalIndex >= digits.length) {
    shifted = `${digits}${"0".repeat(decimalIndex - digits.length)}`;
  } else {
    shifted = `${digits.slice(0, decimalIndex)}.${digits.slice(decimalIndex)}`;
  }

  return normalizeDecimal(`${sign}${shifted}`);
}

export function formatDecimal(value: string, maximumFractionDigits = 8): string {
  return roundDecimal(value, maximumFractionDigits) ?? "Not available";
}

export function formatPercent(value: string | null, undefinedReason?: string | null): string {
  if (value === null) {
    return formatUndefinedMetric(undefinedReason);
  }

  const percentage = shiftDecimal(value, 2);
  if (!percentage) {
    return "Not available";
  }

  return `${roundDecimal(percentage, 4) ?? "Not available"}%`;
}

export function formatSignedPercent(
  value: string | null,
  undefinedReason?: string | null,
): string {
  const formatted = formatPercent(value, undefinedReason);
  if (!formatted.endsWith("%") || formatted.startsWith("-")) {
    return formatted;
  }
  if (formatted === "0%") {
    return formatted;
  }
  return `+${formatted}`;
}

export function formatRate(value: string): string {
  const percentage = shiftDecimal(value, 2);
  return percentage ? `${roundDecimal(percentage, 4) ?? "Not available"}%` : "Not available";
}

export function formatSignedRate(value: string): string {
  const formatted = formatRate(value);
  if (!formatted.endsWith("%") || formatted.startsWith("-")) {
    return formatted;
  }
  if (formatted === "0%") {
    return formatted;
  }
  return `+${formatted}`;
}

export function formatBasisPoints(value: string): string {
  if (!validDecimal(value)) {
    return "Not available";
  }

  const percentage = shiftDecimal(value, -2);
  if (!percentage) {
    return "Not available";
  }

  return `${roundDecimal(percentage, 4) ?? "Not available"}%`;
}

export function formatUndefinedMetric(reason: string | null | undefined): string {
  switch (reason) {
    case "no_trades":
      return "Not defined — no completed trades.";
    case "no_losing_trades":
      return "Not defined — no losing trades.";
    default:
      return reason
        ? `Not defined — ${reason.replaceAll("_", " ")}.`
        : "Not defined.";
  }
}

export function formatFingerprint(value: string): string {
  if (value.length <= 16) {
    return value;
  }
  return `${value.slice(0, 8)}…${value.slice(-8)}`;
}

export function formatAssumptionKey(key: string): string {
  const normalizedKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
  const labels: Record<string, string> = {
    initial_equity: "Initial equity",
    signal_timing: "Signal timing",
    entry_timing: "Entry timing",
    holding_period_candles: "Holding candles",
    position_direction: "Position direction",
    position_sizing: "Position sizing",
    concurrent_positions: "Concurrent positions",
    overlapping_signals: "Overlapping signals",
    entry_slippage_rate: "Entry slippage",
    exit_slippage_rate: "Exit slippage",
    fee_rate: "Fee rate",
    stop_loss: "Stop loss",
    take_profit: "Take profit",
    early_exit: "Early exit",
    end_of_range: "End of range",
    compounding: "Compounding",
    short_loss_cap: "Synthetic-short loss cap",
    schema_version: "Schema version",
  };
  return labels[normalizedKey] ?? normalizedKey.replaceAll("_", " ");
}

export function formatAssumptionValue(key: string, value: unknown): string {
  const normalizedKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
  if (typeof value === "string") {
    if (value === "NaN" || value === "Infinity" || value === "-Infinity") {
      return "Not available";
    }
    if (normalizedKey.endsWith("_rate") || normalizedKey === "fee_rate") {
      return formatRate(value);
    }
    return value.replaceAll("_", " ");
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "number") {
    return String(value);
  }
  return "Not available";
}

export function formatTradeTime(trade: HistoricalAnalysisTrade): string {
  return `${formatUtcDateTime(trade.signalCloseTime)} → ${formatUtcDateTime(trade.exitCloseTime)}`;
}

export function formatEquityPointTime(point: HistoricalAnalysisEquityPoint): string {
  return formatUtcDateTime(point.candleCloseTime);
}
