import { formatDecimal, formatEquityPointTime, formatPositionState } from "./format";
import type { HistoricalAnalysisEquityPoint } from "./types";

type EquityTableProps = {
  error: string | null;
  isLoading: boolean;
  nextCursor: string | null;
  onLoadMore: () => void;
  points: HistoricalAnalysisEquityPoint[];
};

export function EquityTable({
  error,
  isLoading,
  nextCursor,
  onLoadMore,
  points,
}: EquityTableProps) {
  return (
    <div className="space-y-3">
      {error ? <p className="text-sm text-red-700 dark:text-red-300">{error}</p> : null}
      {!isLoading && !points.length ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          No detailed equity points are available.
        </p>
      ) : null}
      {points.length ? (
        <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-700">
          <table className="min-w-full text-left text-sm">
            <caption className="sr-only">
              Detailed immutable hypothetical equity points, ordered by sequence.
            </caption>
            <thead className="bg-zinc-50 dark:bg-zinc-950">
              <tr>
                <th className="px-3 py-2 font-medium" scope="col">
                  UTC candle close
                </th>
                <th className="px-3 py-2 font-medium" scope="col">
                  Equity
                </th>
                <th className="px-3 py-2 font-medium" scope="col">
                  Drawdown
                </th>
                <th className="px-3 py-2 font-medium" scope="col">
                  Position state
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
      ) : null}
      {isLoading ? <p aria-live="polite">Loading detailed equity…</p> : null}
      {nextCursor ? (
        <button
          className="rounded-lg border border-zinc-300 px-4 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
          disabled={isLoading}
          onClick={onLoadMore}
          type="button"
        >
          {isLoading ? "Loading more…" : "Load more equity data"}
        </button>
      ) : null}
    </div>
  );
}
