"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { useAuth } from "@/features/auth/auth-provider";

import { DashboardShell } from "./dashboard-shell";
import { DashboardShellSkeleton } from "./dashboard-shell-skeleton";

export function DashboardGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { error, refreshSession, status } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/sign-in");
    }
  }, [router, status]);

  if (status === "loading") {
    return <DashboardShellSkeleton />;
  }

  if (status === "unauthenticated") {
    if (error) {
      return (
        <main className="flex min-h-svh items-center justify-center bg-background px-6 py-16">
          <section className="w-full max-w-lg space-y-4">
            <h1 className="text-2xl font-semibold">Session unavailable</h1>
            <InlineError
              message={error}
              retryAction={
                <InlineErrorRetryButton
                  onRetry={() => void refreshSession()}
                />
              }
              title="We couldn't restore your session"
            />
          </section>
        </main>
      );
    }

    return (
      <main
        aria-live="polite"
        className="flex min-h-svh items-center justify-center bg-background px-6 py-16"
        role="status"
      >
        Redirecting to sign in…
      </main>
    );
  }

  return <DashboardShell>{children}</DashboardShell>;
}
