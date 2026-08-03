"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { useAuth } from "../features/auth/auth-provider";

export default function Home() {
  const router = useRouter();
  const { error, refreshSession, status } = useAuth();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [router, status]);

  if (status === "loading" || status === "authenticated") {
    return (
      <main
        aria-busy="true"
        aria-label="Loading FreeCoinAlert"
        className="flex min-h-svh items-center justify-center bg-background px-6 py-16"
        role="status"
      >
        <section className="w-full max-w-md space-y-6 text-center">
          <p className="text-sm font-medium tracking-[0.2em] text-muted-foreground uppercase">
            FreeCoinAlert
          </p>
          <Skeleton className="mx-auto h-10 w-64" />
          <Skeleton className="mx-auto h-5 w-full max-w-sm" />
        </section>
      </main>
    );
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-background px-6 py-16 text-foreground">
      <section className="w-full max-w-2xl space-y-6 rounded-xl bg-card p-8 shadow-sm ring-1 ring-foreground/10 sm:p-12">
        <p className="text-sm font-medium tracking-[0.2em] text-muted-foreground uppercase">
          FreeCoinAlert
        </p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          FreeCoinAlert
        </h1>
        <p className="text-lg leading-8 text-muted-foreground">
          Configure cryptocurrency market alerts and receive them through Telegram.
        </p>
        <div className="space-y-4">
          <p className="leading-7 text-muted-foreground">
            Sign in to connect Telegram and manage your market alerts from one dashboard.
          </p>
          {error ? (
            <div aria-live="polite" className="space-y-2">
              <p className="text-sm text-destructive">{error}</p>
              <Button
                onClick={() => void refreshSession()}
                type="button"
                variant="outline"
              >
                Retry session check
              </Button>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href="/sign-up">Sign up</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/sign-in">Sign in</Link>
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
}
