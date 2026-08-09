"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";

export function AuthAwareBacktestCta() {
  const { status } = useAuth();
  const isAuthenticated = status === "authenticated";

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button asChild size="lg">
        <Link href={isAuthenticated ? "/historical-analysis" : "/sign-up"}>
          {isAuthenticated ? "Open backtester" : "Start backtesting"}
        </Link>
      </Button>
      {isAuthenticated ? (
        <Button asChild size="lg" variant="outline">
          <Link href="/dashboard">Dashboard</Link>
        </Button>
      ) : (
        <Button asChild size="lg" variant="outline">
          <Link href="/sign-in">Sign in</Link>
        </Button>
      )}
    </div>
  );
}
