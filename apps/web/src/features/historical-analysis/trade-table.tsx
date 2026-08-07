import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { ResponsiveTable } from "@/components/responsive-table";

import {
  formatDirection,
  formatFixedDecimal,
  formatFixedSignedPercent,
  formatOutcome,
  formatPositionState,
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
    <div aria-busy={isLoading} className="space-y-3">
      {error ? (
        <InlineError
          message={error}
          retryAction={<InlineErrorRetryButton onRetry={onLoadMore} />}
          title="Hypothetical trades are unavailable"
        />
      ) : null}
      {!isLoading && !trades.length && !error ? (
        <p className="text-sm text-muted-foreground">
          This analysis completed with no hypothetical trades in the selected
          range.
        </p>
      ) : null}
      {isLoading && !trades.length ? (
        <div className="space-y-2" role="status">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <span className="sr-only">Loading hypothetical trades</span>
        </div>
      ) : null}
      {trades.length ? (
        <ResponsiveTable caption="Immutable hypothetical trades, ordered by sequence.">
          <Table className="min-w-[1100px]">
            <TableCaption className="sr-only">
              Immutable hypothetical trades, ordered by sequence. Every column
              remains available on narrow screens through horizontal scrolling.
            </TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">Sequence</TableHead>
                <TableHead scope="col">Signal time</TableHead>
                <TableHead scope="col">Direction</TableHead>
                <TableHead scope="col">Entry time / fill</TableHead>
                <TableHead scope="col">Exit time / fill</TableHead>
                <TableHead scope="col">Holding candles</TableHead>
                <TableHead scope="col">Gross return</TableHead>
                <TableHead scope="col">Net return</TableHead>
                <TableHead scope="col">Net PnL</TableHead>
                <TableHead scope="col">Outcome</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trades.map((trade) => (
                <TableRow key={trade.sequence}>
                  <TableCell>{trade.sequence}</TableCell>
                  <TableCell>{formatUtcDateTime(trade.signalCloseTime)}</TableCell>
                  <TableCell>
                    <div>{formatDirection(trade.signalDirection)}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatPositionState(trade.positionDirection)}
                    </div>
                  </TableCell>
                  <TableCell>
                    {formatUtcDateTime(trade.entryOpenTime)}
                    <br />
                    {trade.entryFillPrice}
                  </TableCell>
                  <TableCell>
                    {formatUtcDateTime(trade.exitCloseTime)}
                    <br />
                    {trade.exitFillPrice}
                  </TableCell>
                  <TableCell>{trade.holdingCandleCount}</TableCell>
                  <TableCell>
                    {formatFixedSignedPercent(trade.grossReturn)}
                  </TableCell>
                  <TableCell>
                    {formatFixedSignedPercent(trade.netReturn)}
                  </TableCell>
                  <TableCell>{formatFixedDecimal(trade.netPnl)}</TableCell>
                  <TableCell>{formatOutcome(trade.outcome)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ResponsiveTable>
      ) : null}
      {isLoading && trades.length ? (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          Loading more hypothetical trades…
        </p>
      ) : null}
      {nextCursor ? (
        <Button
          disabled={isLoading}
          onClick={onLoadMore}
          type="button"
          variant="outline"
        >
          {isLoading ? "Loading more…" : "Load more trades"}
        </Button>
      ) : null}
    </div>
  );
}
