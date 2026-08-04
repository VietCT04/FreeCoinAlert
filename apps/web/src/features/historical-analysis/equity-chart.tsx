"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";

import { ResponsiveTable } from "@/components/responsive-table";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Table,
  TableBody,
  TableCell,
  TableCaption,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import {
  formatDecimal,
  formatEquityPointTime,
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

function PreviewTable({ points }: { points: HistoricalAnalysisEquityPoint[] }) {
  return (
    <ResponsiveTable caption="Server-provided hypothetical equity preview data.">
      <Table>
        <TableCaption className="sr-only">
          Server-provided equity preview points with exact values and UTC candle
          closes.
        </TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">UTC candle close</TableHead>
            <TableHead scope="col">Hypothetical equity</TableHead>
            <TableHead scope="col">Drawdown</TableHead>
            <TableHead scope="col">Position</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {points.map((point) => (
            <TableRow key={point.sequence}>
              <TableCell>{formatEquityPointTime(point)}</TableCell>
              <TableCell>{point.equity}</TableCell>
              <TableCell>{point.drawdown}</TableCell>
              <TableCell>{formatPositionState(point.positionState)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </ResponsiveTable>
  );
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
    <div className="space-y-4">
      {canDraw ? (
        <figure aria-labelledby="historical-analysis-equity-chart-title" className="space-y-3">
          <div className="min-h-[260px] w-full rounded-xl border bg-card p-2 sm:p-4">
            <ChartContainer
              aria-label="Hypothetical equity progression chart"
              className="min-h-[260px] w-full aspect-auto"
              config={chartConfig}
            >
              <LineChart
                accessibilityLayer
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
                  tickFormatter={(value) => formatDecimal(String(value))}
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
                              Equity {point.equityExact}
                            </span>
                            <span className="text-muted-foreground">
                              Drawdown {point.drawdownExact} · {formatPositionState(point.positionState)}
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
            Server-provided equity preview. The API may downsample the full
            series to at most 200 points while preserving the first and last
            points; the browser only converts exact values to plotting
            coordinates.
          </figcaption>
        </figure>
      ) : (
        <p className="text-sm text-muted-foreground">
          The equity preview is not available as a drawable numeric series.
        </p>
      )}
      <PreviewTable points={points} />
    </div>
  );
}
