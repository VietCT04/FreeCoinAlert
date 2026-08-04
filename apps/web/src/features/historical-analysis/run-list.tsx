import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import {
  formatStatus,
  formatTimeframe,
  formatUtcDateTime,
} from "./format";
import type { HistoricalAnalysisRun } from "./types";

type RunListProps = {
  headingId?: string;
  isLoading: boolean;
  isLoadingMore: boolean;
  nextCursor: string | null;
  onLoadMore: () => void;
  onSelect: (runId: string) => void;
  runs: HistoricalAnalysisRun[];
  selectedRunId: string | null;
};

export function RunList({
  headingId = "historical-analysis-runs-heading",
  isLoading,
  isLoadingMore,
  nextCursor,
  onLoadMore,
  onSelect,
  runs,
  selectedRunId,
}: RunListProps) {
  return (
    <section aria-labelledby={headingId} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h3 className="text-lg font-semibold" id={headingId}>
            Previous analyses
          </h3>
          <p className="text-sm text-muted-foreground">
            Select an owner-scoped run to inspect its current lifecycle or report.
          </p>
        </div>
        {isLoading ? <span className="text-sm text-muted-foreground">Loading…</span> : null}
      </div>

      {isLoading ? (
        <div aria-busy="true" aria-label="Loading previous analyses" className="space-y-3" role="status">
          {Array.from({ length: 3 }, (_, index) => (
            <Card key={index}>
              <CardContent className="space-y-3 p-4">
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {!isLoading && !runs.length ? (
        <EmptyState
          description="Create a historical analysis to see its lifecycle and report here."
          title="No previous analyses"
        />
      ) : null}

      {runs.length ? (
        <ol className="space-y-3">
          {runs.map((run) => {
            const selected = run.id === selectedRunId;
            const statusLabel = formatStatus(
              run.status,
              run.progressStage,
              run.cancellationRequested,
            );
            const isActive = run.status === "queued" || run.status === "running";

            return (
              <li key={run.id}>
                <Card className={selected ? "ring-2 ring-ring" : undefined}>
                  <button
                    aria-pressed={selected}
                    className="w-full rounded-xl text-left outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                    onClick={() => onSelect(run.id)}
                    type="button"
                  >
                    <CardContent className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto]">
                      <div className="min-w-0 space-y-1">
                        <p className="truncate font-medium">
                          {run.market.symbol} · {run.preset.name} ·{" "}
                          {formatTimeframe(run.preset.timeframe)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {formatUtcDateTime(run.analysisStart)} →{" "}
                          {formatUtcDateTime(run.analysisEnd)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Created {formatUtcDateTime(run.createdAt)}
                        </p>
                      </div>
                      <div className="flex items-start gap-2 sm:flex-col sm:items-end">
                        <StatusBadge status={statusLabel} />
                        {isActive && Number.isFinite(run.progressPercent) ? (
                          <span className="text-xs text-muted-foreground">
                            {run.progressPercent}% server-reported
                          </span>
                        ) : null}
                      </div>
                    </CardContent>
                  </button>
                </Card>
              </li>
            );
          })}
        </ol>
      ) : null}

      {nextCursor ? (
        <Button
          disabled={isLoadingMore}
          onClick={onLoadMore}
          type="button"
          variant="outline"
        >
          {isLoadingMore ? "Loading more…" : "Load more analyses"}
        </Button>
      ) : null}
    </section>
  );
}
