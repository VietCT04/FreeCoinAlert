"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  formatFixedDecimal,
  formatPositionState,
  formatUtcDateTime,
} from "./format";
import type { HistoricalAnalysisEquityPoint } from "./types";

type EquityPlotPoint = {
  closeTime: string;
  drawdownExact: string;
  equityExact: string;
  equityValue: number;
  positionState: string;
  sequence: number;
};

const chartConfig = {
  equityValue: {
    color: "var(--color-chart-2)",
    label: "Hypothetical equity",
  },
} satisfies ChartConfig;

function numericEquity(value: string): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatUtcTick(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return "Unknown";
  }

  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

export function EquityChart({
  points,
}: {
  points: HistoricalAnalysisEquityPoint[];
}) {
  const plotPoints = points.flatMap((point): EquityPlotPoint[] => {
    const equityValue = numericEquity(point.equity);
    return equityValue === null
      ? []
      : [
          {
            closeTime: point.candleCloseTime,
            drawdownExact: point.drawdown,
            equityExact: point.equity,
            equityValue,
            positionState: point.positionState,
            sequence: point.sequence,
          },
        ];
  });
  const canDraw = points.length > 0 && plotPoints.length === points.length;

  return (
    <>
      {canDraw ? (
        <figure aria-labelledby="historical-analysis-equity-chart-title" className="space-y-3">
          <div className="min-h-[260px] w-full rounded-xl border bg-card p-2 sm:p-4">
            <ChartContainer
              className="h-[300px] min-h-0 w-full aspect-auto sm:h-[340px]"
              config={chartConfig}
            >
              <LineChart
                data={plotPoints}
                margin={{ bottom: 8, left: 4, right: 12, top: 8 }}
              >
                <CartesianGrid vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="sequence"
                  minTickGap={28}
                  tickFormatter={(sequence) => {
                    const point = plotPoints.find(
                      (item) => item.sequence === Number(sequence),
                    );
                    return point ? formatUtcTick(point.closeTime) : "";
                  }}
                  tickLine={false}
                />
                <YAxis
                  axisLine={false}
                  domain={["auto", "auto"]}
                  tickFormatter={(value) => formatFixedDecimal(String(value))}
                  tickLine={false}
                  width={72}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      hideLabel
                      formatter={(_value, _name, item) => {
                        const point = item.payload as EquityPlotPoint;
                        return (
                          <div className="grid gap-1">
                            <span className="text-muted-foreground">
                              {formatUtcDateTime(point.closeTime)}
                            </span>
                            <span className="font-mono font-medium text-foreground">
                              Equity {formatFixedDecimal(point.equityExact)}
                            </span>
                            <span className="text-muted-foreground">
                              Drawdown {formatFixedDecimal(point.drawdownExact)} ·{" "}
                              {formatPositionState(point.positionState)}
                            </span>
                          </div>
                        );
                      }}
                    />
                  }
                />
                <Line
                  dataKey="equityValue"
                  dot={false}
                  isAnimationActive={false}
                  stroke="var(--color-equityValue)"
                  strokeWidth={2}
                  type="monotone"
                />
              </LineChart>
            </ChartContainer>
          </div>
          <figcaption className="text-sm text-muted-foreground" id="historical-analysis-equity-chart-title">
            Server-provided equity preview for the selected range.
          </figcaption>
        </figure>
      ) : (
        <p className="text-sm text-muted-foreground">
          The equity preview is not available as a drawable numeric series.
        </p>
      )}
    </>
  );
}
