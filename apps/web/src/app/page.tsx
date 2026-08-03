"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { useAuth } from "../features/auth/auth-provider";
import { PriceAlertPanel } from "../features/alerts/price-alert-panel";
import { HistoricalAnalysisPanel } from "../features/historical-analysis/historical-analysis-panel";
import { PresetSignalPanel } from "../features/signals/preset-signal-panel";
import { TelegramConnectionPanel } from "../features/telegram/connection-panel";

export default function Home() {
  const { error, refreshSession, signOut, status, user } = useAuth();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [telegramConnectionRevision, setTelegramConnectionRevision] =
    useState(0);

  const handleTelegramConnectionChanged = useCallback(() => {
    setTelegramConnectionRevision((current) => current + 1);
  }, []);

  async function handleSignOut() {
    if (isSigningOut) {
      return;
    }

    setIsSigningOut(true);
    await signOut();
    setIsSigningOut(false);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6 py-16 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-50">
      <section className="w-full max-w-2xl space-y-6 rounded-2xl bg-white p-8 shadow-sm ring-1 ring-zinc-200 sm:p-12 dark:bg-zinc-900 dark:ring-zinc-800">
        <p className="text-sm font-medium tracking-[0.2em] text-zinc-500 uppercase">
          FreeCoinAlert
        </p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          FreeCoinAlert
        </h1>
        <p className="text-lg leading-8 text-zinc-600 dark:text-zinc-300">
          Configure cryptocurrency market alerts and receive them through Telegram.
        </p>
        {status === "loading" ? <p>Checking your session…</p> : null}
        {status === "unauthenticated" ? (
          <div className="space-y-4">
            <p className="leading-7 text-zinc-600 dark:text-zinc-300">
              Sign in to connect Telegram and manage your price alerts.
            </p>
            {error ? (
              <div className="space-y-2" aria-live="polite">
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
                <button
                  className="rounded-lg border border-zinc-300 px-4 py-2 font-medium dark:border-zinc-700"
                  onClick={() => void refreshSession()}
                  type="button"
                >
                  Retry session check
                </button>
              </div>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <Link
                className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white dark:bg-zinc-50 dark:text-zinc-900"
                href="/sign-up"
              >
                Sign up
              </Link>
              <Link
                className="rounded-lg border border-zinc-300 px-4 py-2 font-medium dark:border-zinc-700"
                href="/sign-in"
              >
                Sign in
              </Link>
            </div>
          </div>
        ) : null}
        {status === "authenticated" && user ? (
          <div className="space-y-4">
            <p className="leading-7 text-zinc-600 dark:text-zinc-300">
              Signed in as {user.email}
            </p>
            <p aria-live="polite" className="text-sm text-red-700 dark:text-red-300">
              {error}
            </p>
            <TelegramConnectionPanel
              onConnectionChanged={handleTelegramConnectionChanged}
            />
            <PriceAlertPanel />
            <PresetSignalPanel
              telegramConnectionRevision={telegramConnectionRevision}
            />
            <HistoricalAnalysisPanel />
            <button
              className="rounded-lg border border-zinc-300 px-4 py-2 font-medium disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
              disabled={isSigningOut}
              onClick={() => void handleSignOut()}
              type="button"
            >
              {isSigningOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        ) : null}
      </section>
    </main>
  );
}
