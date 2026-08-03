import {
  formatStatus,
  formatTimeframe,
  formatUtcDateTime,
} from "./format";
import type { HistoricalAnalysisRun } from "./types";

type RunListProps = {
  isLoading: boolean;
  isLoadingMore: boolean;
  nextCursor: string | null;
  onLoadMore: () => void;
  onSelect: (runId: string) => void;
  runs: HistoricalAnalysisRun[];
  selectedRunId: string | null;
};

export function RunList({
  isLoading,
  isLoadingMore,
  nextCursor,
  onLoadMore,
  onSelect,
  runs,
  selectedRunId,
}: RunListProps) {
  return (
    <section aria-labelledby="historical-analysis-runs-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-lg font-semibold" id="historical-analysis-runs-heading">
          Recent analyses
        </h3>
        {isLoading ? <span aria-live="polite">Loading…</span> : null}
      </div>

      {!isLoading && !runs.length ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          No historical analyses yet. Create one above to see its lifecycle and
          report here.
        </p>
      ) : null}

      {runs.length ? (
        <ol className="space-y-3">
          {runs.map((run) => {
            const selected = run.id === selectedRunId;
            return (
              <li key={run.id}>
                <button
                  aria-pressed={selected}
                  className={`w-full rounded-lg border p-4 text-left transition-colors ${
                    selected
                      ? "border-zinc-900 dark:border-zinc-100"
                      : "border-zinc-200 hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-500"
                  }`}
                  onClick={() => onSelect(run.id)}
                  type="button"
                >
                  <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
                    <div className="space-y-1">
                      <p className="font-medium">
                        {run.market.symbol} · {run.preset.name} · {formatTimeframe(run.preset.timeframe)}
                      </p>
                      <p className="text-sm text-zinc-600 dark:text-zinc-300">
                        {formatUtcDateTime(run.analysisStart)} → {formatUtcDateTime(run.analysisEnd)}
                      </p>
                      <p className="text-sm text-zinc-600 dark:text-zinc-300">
                        Created {formatUtcDateTime(run.createdAt)}
                      </p>
                    </div>
                    <div className="text-sm sm:text-right">
                      <p className="font-medium">
                        {formatStatus(run.status, run.progressStage, run.cancellationRequested)}
                      </p>
                      {run.status === "queued" || run.status === "running" ? (
                        <p>{run.progressPercent}%</p>
                      ) : null}
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ol>
      ) : null}

      {nextCursor ? (
        <button
          className="rounded-lg border border-zinc-300 px-4 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
          disabled={isLoadingMore}
          onClick={onLoadMore}
          type="button"
        >
          {isLoadingMore ? "Loading more…" : "Load more analyses"}
        </button>
      ) : null}
    </section>
  );
}
