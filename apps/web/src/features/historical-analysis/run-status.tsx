import { historicalAnalysisFailureMessage } from "./errors";
import { formatStatus } from "./format";
import type { HistoricalAnalysisRun } from "./types";

export function RunStatus({ run }: { run: HistoricalAnalysisRun }) {
  const label = formatStatus(
    run.status,
    run.progressStage,
    run.cancellationRequested,
  );
  const failureMessage = historicalAnalysisFailureMessage(run.failureCode);
  const isActive = run.status === "queued" || run.status === "running";

  return (
    <div className="space-y-2" aria-live="polite">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{label}</span>
        {isActive ? <span>{run.progressPercent}%</span> : null}
      </div>
      {isActive ? (
        <progress
          aria-label={`${label} progress`}
          className="h-2 w-full"
          max={100}
          value={run.progressPercent}
        />
      ) : null}
      {failureMessage ? (
        <p className="text-sm text-red-700 dark:text-red-300">{failureMessage}</p>
      ) : null}
    </div>
  );
}
