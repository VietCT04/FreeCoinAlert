import {
  formatDecimal,
  formatDirection,
  formatOutcome,
  formatPositionState,
  formatSignedRate,
  formatUtcDateTime,
} from "./format";
import type { HistoricalAnalysisTrade } from "./types";

type TradeTableProps = {
  error: string | null;
  isLoading: boolean;
  nextCursor: string | null;
  onLoadMore: () => void;
  trades: HistoricalAnalysisTrade[];
};

export function TradeTable({
  error,
  isLoading,
  nextCursor,
  onLoadMore,
  trades,
}: TradeTableProps) {
  return (
    <div className="space-y-3">
      {error ? <p className="text-sm text-red-700 dark:text-red-300">{error}</p> : null}
      {!isLoading && !trades.length ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          This analysis completed with no hypothetical trades in the selected range.
        </p>
      ) : null}
      {trades.length ? (
        <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-700">
          <table className="min-w-[1100px] text-left text-sm">
            <caption className="sr-only">
              Immutable hypothetical trades, ordered by sequence.
            </caption>
            <thead className="bg-zinc-50 dark:bg-zinc-950">
              <tr>
                <th className="px-3 py-2 font-medium" scope="col">Sequence</th>
                <th className="px-3 py-2 font-medium" scope="col">Signal time</th>
                <th className="px-3 py-2 font-medium" scope="col">Direction</th>
                <th className="px-3 py-2 font-medium" scope="col">Entry time / fill</th>
                <th className="px-3 py-2 font-medium" scope="col">Exit time / fill</th>
                <th className="px-3 py-2 font-medium" scope="col">Holding candles</th>
                <th className="px-3 py-2 font-medium" scope="col">Gross return</th>
                <th className="px-3 py-2 font-medium" scope="col">Net return</th>
                <th className="px-3 py-2 font-medium" scope="col">Net PnL</th>
                <th className="px-3 py-2 font-medium" scope="col">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr className="border-t border-zinc-200 dark:border-zinc-700" key={trade.sequence}>
                  <td className="px-3 py-2">{trade.sequence}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {formatUtcDateTime(trade.signalCloseTime)}
                  </td>
                  <td className="px-3 py-2">
                    <div>{formatDirection(trade.signalDirection)}</div>
                    <div className="text-xs text-zinc-600 dark:text-zinc-300">
                      {formatPositionState(trade.positionDirection)}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {formatUtcDateTime(trade.entryOpenTime)}
                    <br />
                    {formatDecimal(trade.entryFillPrice)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {formatUtcDateTime(trade.exitCloseTime)}
                    <br />
                    {formatDecimal(trade.exitFillPrice)}
                  </td>
                  <td className="px-3 py-2">{trade.holdingCandleCount}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {formatSignedRate(trade.grossReturn)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {formatSignedRate(trade.netReturn)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {formatDecimal(trade.netPnl)}
                  </td>
                  <td className="px-3 py-2">{formatOutcome(trade.outcome)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {isLoading ? <p aria-live="polite">Loading hypothetical trades…</p> : null}
      {nextCursor ? (
        <button
          className="rounded-lg border border-zinc-300 px-4 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
          disabled={isLoading}
          onClick={onLoadMore}
          type="button"
        >
          {isLoading ? "Loading more…" : "Load more trades"}
        </button>
      ) : null}
    </div>
  );
}
