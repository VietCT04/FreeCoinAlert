"use client";

import { Button } from "../../components/ui/button";

export default function DashboardError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-[60vh] items-center justify-center px-4 py-12">
      <section className="w-full max-w-lg space-y-4 text-center">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-muted-foreground">
          This page could not be loaded safely. Try again or choose another dashboard destination.
        </p>
        <Button onClick={reset} type="button">
          Try again
        </Button>
      </section>
    </main>
  );
}
