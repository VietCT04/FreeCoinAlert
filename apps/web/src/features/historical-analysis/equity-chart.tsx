import {
  formatDecimal,
  formatEquityPointTime,
  formatPositionState,
} from "./format";
import type { HistoricalAnalysisEquityPoint } from "./types";

function numericEquity(value: string): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function PreviewTable({ points }: { points: HistoricalAnalysisEquityPoint[] }) {
  return (
    <div className="max-h-72 overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-700">
      <table className="min-w-full text-left text-sm">
        <caption className="sr-only">
          Accessible table of the server-provided equity preview points.
        </caption>
        <thead className="bg-zinc-50 dark:bg-zinc-950">
          <tr>
            <th className="px-3 py-2 font-medium" scope="col">
              UTC candle close
            </th>
            <th className="px-3 py-2 font-medium" scope="col">
              Hypothetical equity
            </th>
            <th className="px-3 py-2 font-medium" scope="col">
              Drawdown
            </th>
            <th className="px-3 py-2 font-medium" scope="col">
              Position
            </th>
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr className="border-t border-zinc-200 dark:border-zinc-700" key={point.sequence}>
              <td className="whitespace-nowrap px-3 py-2">
                {formatEquityPointTime(point)}
              </td>
              <td className="whitespace-nowrap px-3 py-2">
                {formatDecimal(point.equity)}
              </td>
              <td className="whitespace-nowrap px-3 py-2">
                {formatDecimal(point.drawdown)}
              </td>
              <td className="px-3 py-2">{formatPositionState(point.positionState)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EquityChart({
  points,
}: {
  points: HistoricalAnalysisEquityPoint[];
}) {
  const values = points.map((point) => numericEquity(point.equity));
  const canDraw = points.length > 0 && values.every((value) => value !== null);
  const numericValues = values.filter((value): value is number => value !== null);
  const minimum = numericValues.length ? Math.min(...numericValues) : 0;
  const maximum = numericValues.length ? Math.max(...numericValues) : 1;
  const valueRange = maximum - minimum || 1;
  const plotWidth = 640;
  const plotHeight = 170;
  const plotLeft = 58;
  const plotTop = 24;
  const polyline = canDraw
    ? values
        .map((value, index) => {
          const x = plotLeft + (index / Math.max(points.length - 1, 1)) * plotWidth;
          const y = plotTop + plotHeight - ((value ?? minimum) - minimum) / valueRange * plotHeight;
          return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(" ")
    : "";

  return (
    <div className="space-y-4">
      {canDraw ? (
        <figure aria-labelledby="historical-analysis-equity-chart-title" className="space-y-2">
          <svg
            aria-describedby="historical-analysis-equity-chart-caption"
            className="h-auto w-full rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-950"
            role="img"
            viewBox="0 0 760 250"
          >
            <title id="historical-analysis-equity-chart-title">
              Hypothetical equity progression
            </title>
            <line
              stroke="currentColor"
              strokeWidth="1"
              x1={plotLeft}
              x2={plotLeft}
              y1={plotTop}
              y2={plotTop + plotHeight}
            />
            <line
              stroke="currentColor"
              strokeWidth="1"
              x1={plotLeft}
              x2={plotLeft + plotWidth}
              y1={plotTop + plotHeight}
              y2={plotTop + plotHeight}
            />
            <polyline
              fill="none"
              points={polyline}
              stroke="currentColor"
              strokeWidth="2"
            />
            <text fill="currentColor" fontSize="12" textAnchor="middle" x="380" y="238">
              UTC candle close
            </text>
            <text
              fill="currentColor"
              fontSize="12"
              textAnchor="middle"
              transform="rotate(-90 14 110)"
              x="14"
              y="110"
            >
              Hypothetical equity
            </text>
            <text fill="currentColor" fontSize="11" x={plotLeft + 4} y={plotTop - 6}>
              {formatDecimal(String(maximum))}
            </text>
            <text
              fill="currentColor"
              fontSize="11"
              x={plotLeft + 4}
              y={plotTop + plotHeight - 4}
            >
              {formatDecimal(String(minimum))}
            </text>
          </svg>
          <figcaption
            className="text-sm text-zinc-600 dark:text-zinc-300"
            id="historical-analysis-equity-chart-caption"
          >
            Server-provided equity preview. The API may downsample the full
            series to at most 200 points while preserving the first and last
            points; the browser does not recalculate metrics.
          </figcaption>
        </figure>
      ) : (
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          The equity preview is not available as a drawable numeric series.
        </p>
      )}
      <PreviewTable points={points} />
    </div>
  );
}
