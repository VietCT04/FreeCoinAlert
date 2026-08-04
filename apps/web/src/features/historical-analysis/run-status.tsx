import type { ReactNode } from "react";

import { StatusBadge } from "@/components/status-badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { historicalAnalysisFailureMessage } from "./errors";
import { formatStatus, formatUtcDateTime } from "./format";
import type { HistoricalAnalysisRun } from "./types";

function timestampLabel(
  label: string,
  value: string | null,
): ReactNode {
  return value ? (
    <div>
      <dt className="font-medium">{label}</dt>
      <dd className="text-muted-foreground">{formatUtcDateTime(value)}</dd>
    </div>
  ) : null;
}

export function RunStatus({ run }: { run: HistoricalAnalysisRun }) {
  const label = formatStatus(
    run.status,
    run.progressStage,
    run.cancellationRequested,
  );
  const failureMessage = historicalAnalysisFailureMessage(run.failureCode);
  const isActive = run.status === "queued" || run.status === "running";
  const hasServerProgress = Number.isFinite(run.progressPercent);

  return (
    <Card aria-live="polite">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle id="historical-analysis-run-status-heading" tabIndex={-1}>
              Run status
            </CardTitle>
            <CardDescription>
              Server-owned lifecycle state for the selected analysis.
            </CardDescription>
          </div>
          <StatusBadge status={label} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isActive ? (
          <div className="space-y-1 text-sm">
            <p>
              {run.status === "queued"
                ? "The analysis is queued for the bounded worker."
                : "The analysis is running in the bounded worker."}
            </p>
            {hasServerProgress ? (
              <p className="text-muted-foreground">
                Server-reported progress: {run.progressPercent}%
              </p>
            ) : null}
            {run.cancellationRequested ? (
              <p className="text-muted-foreground">
                Cancellation was requested. Running work stops at its next safe
                checkpoint.
              </p>
            ) : null}
          </div>
        ) : null}
        {failureMessage ? (
          <p className="text-sm text-destructive">{failureMessage}</p>
        ) : null}
        {run.status === "cancelled" ? (
          <p className="text-sm text-muted-foreground">
            No report was created for this cancelled analysis.
          </p>
        ) : null}
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          {timestampLabel("Created", run.createdAt)}
          {timestampLabel("Started", run.startedAt)}
          {timestampLabel("Completed", run.completedAt)}
          {timestampLabel("Failed", run.failedAt)}
          {timestampLabel("Cancelled", run.cancelledAt)}
        </dl>
      </CardContent>
    </Card>
  );
}
