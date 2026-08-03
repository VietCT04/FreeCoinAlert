"use client";

import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useAuth } from "@/features/auth/auth-provider";

import { AppSidebar } from "./app-sidebar";
import { SiteHeader } from "./site-header";

export function DashboardShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { error, signOut, user } = useAuth();
  const [isSigningOut, setIsSigningOut] = useState(false);

  async function handleSignOut() {
    if (isSigningOut) {
      return;
    }

    setIsSigningOut(true);
    const signedOut = await signOut();
    setIsSigningOut(false);

    if (signedOut) {
      router.replace("/sign-in");
    }
  }

  return (
    <>
      <a
        className="sr-only fixed top-2 left-2 z-50 rounded-md bg-background px-3 py-2 text-sm font-medium text-foreground shadow-md ring-1 ring-border focus:not-sr-only focus:outline-none focus:ring-2 focus:ring-ring"
        href="#dashboard-main"
      >
        Skip to main content
      </a>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset id="dashboard-main" tabIndex={-1}>
          <SiteHeader
            isSigningOut={isSigningOut}
            onSignOut={() => void handleSignOut()}
            userEmail={user?.email ?? "Account"}
          />
          {error ? (
            <div className="mx-auto w-full max-w-screen-2xl px-4 pt-4 md:px-6">
              <InlineError
                message={error}
                retryAction={
                  <InlineErrorRetryButton
                    disabled={isSigningOut}
                    onRetry={() => void handleSignOut()}
                  />
                }
                title="Account action failed"
              />
            </div>
          ) : null}
          <div className="mx-auto w-full max-w-screen-2xl flex-1 p-4 md:p-6">
            {children}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </>
  );
}
