"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";

import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { PageHeader } from "@/components/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RefreshCw } from "lucide-react";

import { useAuth } from "../auth/auth-provider";
import { useMarkets } from "../markets/use-markets";
import { CreatePriceAlertDialog } from "./create-price-alert-dialog";
import { PriceAlertList } from "./price-alert-list";
import type { PriceAlertStatus } from "./types";
import { usePriceAlerts } from "./use-price-alerts";

type PriceAlertStatusFilter = PriceAlertStatus | "all";

const statusFilters: Array<{
  label: string;
  value: PriceAlertStatusFilter;
}> = [
  { label: "All", value: "all" },
  { label: "Active", value: "active" },
  { label: "Triggered", value: "triggered" },
  { label: "Disabled", value: "disabled" },
  { label: "Failed", value: "failed" },
];

function filterLabel(value: PriceAlertStatusFilter): string {
  return statusFilters.find((filter) => filter.value === value)?.label ?? "All";
}

export function PriceAlertPanel() {
  const { csrfToken, refreshSession, status } = useAuth();
  const markets = useMarkets(status);
  const [statusFilter, setStatusFilter] = useState<PriceAlertStatusFilter>("all");
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const alerts = usePriceAlerts({
    authStatus: status,
    csrfToken,
    refreshSession,
    statusFilter,
  });

  const readyMarkets = markets.markets.filter(
    (market) => market.status === "available" && market.priceRules,
  );

  const handleCreate = useCallback(
    async (request: Parameters<typeof alerts.create>[0]): Promise<boolean> => {
      const created = await alerts.create(request);
      if (!created) return false;

      if (statusFilter !== "all" && statusFilter !== "active") {
        setStatusFilter("active");
      }
      setAnnouncement("Price alert created.");
      toast.success("Price alert created.");
      return true;
    },
    [alerts.create, statusFilter],
  );

  const handleDelete = useCallback(
    async (alertId: string): Promise<boolean> => {
      const deleted = await alerts.remove(alertId);
      if (deleted) {
        setAnnouncement("Price alert deleted.");
        toast.success("Price alert deleted.");
      }
      return deleted;
    },
    [alerts.remove],
  );

  if (status !== "authenticated") {
    return null;
  }

  const currentFilterLabel = filterLabel(statusFilter);
  const createDisabled = markets.isLoading || Boolean(markets.error) || !readyMarkets.length;

  return (
    <div className="space-y-6">
      <PageHeader
        description={
          "Create one-time crossing alerts for supported Binance Spot markets. " +
          "Alerts are delivered through Telegram."
        }
        primaryAction={
          <CreatePriceAlertDialog
            connection={alerts.connection}
            disabled={createDisabled}
            error={alerts.error}
            isCreating={alerts.isCreating}
            markets={markets.markets}
            onCreate={handleCreate}
            onOpenChange={setIsCreateDialogOpen}
          />
        }
        secondaryActions={
          <Button
            aria-busy={alerts.isRefreshing}
            disabled={alerts.isRefreshing}
            onClick={() => void alerts.refreshAlerts()}
            type="button"
            variant="outline"
          >
            <RefreshCw />
            {alerts.isRefreshing ? "Refreshing…" : "Refresh"}
          </Button>
        }
        title="Price Alerts"
      />

      <div aria-live="polite" className="sr-only">
        {announcement}
      </div>

      {markets.error ? (
        <InlineError
          message="Supported market information is unavailable, so new alerts cannot be created."
          retryAction={
            <InlineErrorRetryButton onRetry={() => void markets.refreshMarkets()} />
          }
          title="Market catalogue unavailable"
        />
      ) : null}

      {!markets.isLoading && !markets.error && !readyMarkets.length ? (
        <Alert>
          <AlertTitle>Price alerts are unavailable</AlertTitle>
          <AlertDescription>
            No supported market is currently ready for alert creation.
          </AlertDescription>
        </Alert>
      ) : null}

      {alerts.hasPendingDeliveryPastLimit ? (
        <Alert>
          <AlertTitle>Telegram delivery is still pending</AlertTitle>
          <AlertDescription>
            Refresh the selected alert list for the latest server-confirmed status.
          </AlertDescription>
        </Alert>
      ) : null}

      <Tabs
        onValueChange={(value) => setStatusFilter(value as PriceAlertStatusFilter)}
        value={statusFilter}
      >
        <TabsList className="w-full flex-wrap justify-start sm:w-auto" variant="line">
          {statusFilters.map((filter) => (
            <TabsTrigger key={filter.value} value={filter.value}>
              {filter.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {alerts.error && !isCreateDialogOpen ? (
        <InlineError
          message={alerts.error}
          retryAction={
            <InlineErrorRetryButton onRetry={() => void alerts.refreshAlerts()} />
          }
          title="Price alerts could not be loaded"
        />
      ) : null}

      <section aria-labelledby="price-alert-collection-heading" className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold" id="price-alert-collection-heading">
            {currentFilterLabel} alerts
          </h2>
          <p className="text-sm text-muted-foreground">
            Server-confirmed alerts in the selected lifecycle view.
          </p>
        </div>
        {alerts.isInitialLoading ? (
          <div aria-busy="true" aria-label="Loading price alerts" role="status">
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          <PriceAlertList
            alerts={alerts.alerts}
            filterLabel={currentFilterLabel}
            isLoadingMore={alerts.isLoadingMore}
            nextCursor={alerts.nextCursor}
            onDelete={handleDelete}
            onLoadMore={alerts.loadMore}
          />
        )}
      </section>
    </div>
  );
}
