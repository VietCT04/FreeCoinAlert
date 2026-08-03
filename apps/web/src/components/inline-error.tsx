import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

type InlineErrorProps = {
  message: string;
  title?: string;
  retryAction?: ReactNode;
};

export function InlineError({
  message,
  title = "Something went wrong",
  retryAction,
}: InlineErrorProps) {
  return (
    <Alert aria-live="assertive" variant="destructive">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
        <span>{message}</span>
        {retryAction}
      </AlertDescription>
    </Alert>
  );
}

export function InlineErrorRetryButton({
  onRetry,
  disabled = false,
}: {
  onRetry: () => void;
  disabled?: boolean;
}) {
  return (
    <Button onClick={onRetry} size="sm" type="button" variant="outline" disabled={disabled}>
      Try again
    </Button>
  );
}
