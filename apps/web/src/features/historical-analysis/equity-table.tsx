import { ResponsiveTable } from "@/components/responsive-table";
import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { formatEquityPointTime, formatPositionState } from "./format";
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
    <div aria-busy={isLoading} className="space-y-3">
      {error ? (
        <InlineError
          message={error}
          retryAction={<InlineErrorRetryButton onRetry={onLoadMore} />}
          title="Detailed equity is unavailable"
        />
      ) : null}
      {!isLoading && !points.length && !error ? (
        <p className="text-sm text-muted-foreground">
          No detailed equity points are available.
        </p>
      ) : null}
      {isLoading && !points.length ? (
        <div className="space-y-2" role="status">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <span className="sr-only">Loading detailed equity</span>
        </div>
      ) : null}
      {points.length ? (
        <ResponsiveTable caption="Detailed immutable hypothetical equity points.">
          <Table className="min-w-[720px]">
            <TableCaption className="sr-only">
              Detailed immutable hypothetical equity points, preserving exact
              server strings and UTC candle close times.
            </TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead scope="col">UTC candle close</TableHead>
                <TableHead scope="col">Equity</TableHead>
                <TableHead scope="col">Drawdown</TableHead>
                <TableHead scope="col">Position state</TableHead>
                <TableHead scope="col">Active trade</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {points.map((point) => (
                <TableRow key={point.sequence}>
                  <TableCell>{formatEquityPointTime(point)}</TableCell>
                  <TableCell>{point.equity}</TableCell>
                  <TableCell>{point.drawdown}</TableCell>
                  <TableCell>{formatPositionState(point.positionState)}</TableCell>
                  <TableCell>{point.activeTradeSequence ?? "None"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ResponsiveTable>
      ) : null}
      {isLoading && points.length ? (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          Loading more detailed equity…
        </p>
      ) : null}
      {nextCursor ? (
        <Button
          disabled={isLoading}
          onClick={onLoadMore}
          type="button"
          variant="outline"
        >
          {isLoading ? "Loading more…" : "Load more equity data"}
        </Button>
      ) : null}
    </div>
  );
}
