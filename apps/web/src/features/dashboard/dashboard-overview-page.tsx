"use client";

import Link from "next/link";
import {
  Activity,
  BellRing,
  CircleAlert,
  LayoutDashboard,
  RefreshCw,
  Send,
} from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/empty-state";
import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { MetricCard } from "@/components/metric-card";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/features/auth/auth-provider";

import type { DashboardActivityItem, DashboardMetric } from "./types";
import { useDashboardOverview } from "./use-dashboard-overview";

function formatActivityDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "Unknown UTC time"
    : date.toLocaleString(undefined, {
        timeZone: "UTC",
        timeZoneName: "short",
      });
}

function telegramLabel(status: string): string {
  switch (status) {
    case "connected":
      return "Connected";
    case "linking":
      return "Linking";
    case "degraded":
      return "Needs attention";
    case "not_connected":
    case "disconnected":
    default:
      return "Not connected";
  }
}

function OverviewMetric<T>({
  icon,
  label,
  metric,
  renderValue,
  supportingText,
}: {
  icon: ReactNode;
  label: string;
  metric: DashboardMetric<T>;
  renderValue: (value: T) => ReactNode;
  supportingText: (value: T) => ReactNode;
}) {
  const value = metric.isLoading ? (
    <Skeleton className="h-8 w-24" />
  ) : metric.error ? (
    <span className="text-base font-medium">Unavailable</span>
  ) : metric.value === null ? (
    <span className="text-base font-medium">Unavailable</span>
  ) : (
    renderValue(metric.value)
  );

  const support =
    metric.error || metric.value === null
      ? "Try refreshing when the service is available."
      : supportingText(metric.value);

  return (
    <MetricCard
      icon={icon}
      label={label}
      supportingText={support}
      value={value}
    />
  );
}

function activityIcon(item: DashboardActivityItem) {
  if (item.kind === "price_alert_triggered") {
    return BellRing;
  }

  if (item.kind === "signal_invalidated") {
    return CircleAlert;
  }

  return Activity;
}

function RecentActivity({
  items,
  error,
  isLoading,
  onRetry,
}: {
  items: DashboardActivityItem[];
  error: string | null;
  isLoading: boolean;
  onRetry: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent activity</CardTitle>
        <CardDescription>
          Owner-visible alert triggers and preset-signal events. Telegram delivery history is not shown here.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div aria-label="Loading recent activity" className="space-y-4" role="status">
            {Array.from({ length: 3 }, (_, index) => (
              <div className="flex items-start gap-3" key={index}>
                <Skeleton className="mt-1 size-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-4 w-full max-w-md" />
                </div>
              </div>
            ))}
          </div>
        ) : null}
        {!isLoading && error ? (
          <InlineError
            message={error}
            retryAction={<InlineErrorRetryButton onRetry={onRetry} />}
            title="Recent activity is unavailable"
          />
        ) : null}
        {!isLoading && !items.length && !error ? (
          <EmptyState
            icon={<LayoutDashboard />}
            title="No recent activity"
            description="Triggered alerts and visible preset-signal events will appear here when available."
          />
        ) : null}
        {!isLoading && items.length ? (
          <ul className="divide-y divide-border">
            {items.map((item) => {
              const Icon = activityIcon(item);

              return (
                <li key={item.id}>
                  <Link
                    className="flex items-start gap-3 py-4 first:pt-0 last:pb-0 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    href={item.href}
                  >
                    <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                      <Icon aria-hidden="true" className="size-4" />
                    </span>
                    <span className="min-w-0 flex-1 space-y-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{item.title}</span>
                        <StatusBadge status={item.statusLabel} />
                      </span>
                      <span className="block break-words text-sm text-muted-foreground">
                        {item.description}
                      </span>
                      <time
                        className="block text-xs text-muted-foreground"
                        dateTime={item.occurredAt}
                      >
                        {formatActivityDate(item.occurredAt)}
                      </time>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function DashboardOverviewPage() {
  const { refreshSession, status } = useAuth();
  const overview = useDashboardOverview({
    authStatus: status,
    refreshSession,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        description="A concise view of monitoring readiness, active subscriptions, and owner-visible activity."
        primaryAction={
          <Button asChild>
            <Link href="/price-alerts">
              <BellRing aria-hidden="true" />
              Create price alert
            </Link>
          </Button>
        }
        secondaryActions={
          <>
            <Button asChild variant="outline">
              <Link href="/preset-signals">
                <Activity aria-hidden="true" />
                Browse preset signals
              </Link>
            </Button>
            <Button
              disabled={overview.isRefreshing}
              onClick={() => void overview.refresh()}
              type="button"
              variant="ghost"
            >
              <RefreshCw aria-hidden="true" />
              {overview.isRefreshing ? "Refreshing…" : "Refresh"}
            </Button>
          </>
        }
        title="Overview"
      />

      <section aria-labelledby="dashboard-summary-heading" className="space-y-4">
        <h2 className="sr-only" id="dashboard-summary-heading">
          Dashboard summary
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <OverviewMetric
            icon={<BellRing />}
            label="Active price alerts"
            metric={overview.activeAlerts}
            renderValue={(value) => value}
            supportingText={() => "Up to 20 active alerts are allowed."}
          />
          <OverviewMetric
            icon={<Activity />}
            label="Active preset subscriptions"
            metric={overview.activeSubscriptions}
            renderValue={(value) => value}
            supportingText={() => "Fixed signal subscriptions currently enabled."}
          />
          <OverviewMetric
            icon={<Send />}
            label="Telegram"
            metric={overview.telegram}
            renderValue={(value) => telegramLabel(value.status)}
            supportingText={(value) => `Server status: ${value.status}`}
          />
          <OverviewMetric
            icon={<LayoutDashboard />}
            label="Supported markets ready"
            metric={overview.markets}
            renderValue={(value) => `${value.available} / ${value.total}`}
            supportingText={() => "Catalogue readiness, not live-stream health."}
          />
        </div>
      </section>

      <RecentActivity
        error={overview.activity.error}
        isLoading={overview.activity.isLoading}
        items={overview.activity.items}
        onRetry={() => void overview.refresh()}
      />
    </div>
  );
}
