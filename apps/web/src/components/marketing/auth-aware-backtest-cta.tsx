"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";

type AuthAwareBacktestCtaProps = {
  showSecondary?: boolean;
};

export function AuthAwareBacktestCta({
  showSecondary = true,
}: AuthAwareBacktestCtaProps) {
  const { status } = useAuth();
  const isAuthenticated = status === "authenticated";

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button asChild size="lg">
        <Link href={isAuthenticated ? "/historical-analysis" : "/sign-up"}>
          {isAuthenticated ? "Open backtester" : "Start backtesting"}
        </Link>
      </Button>
      {showSecondary ? (
        isAuthenticated ? (
          <Button asChild size="lg" variant="outline">
            <Link href="/dashboard">Dashboard</Link>
          </Button>
        ) : (
          <Button asChild size="lg" variant="outline">
            <Link href="/sign-in">Sign in</Link>
          </Button>
        )
      ) : null}
    </div>
  );
}
