"use client";

import { EmptyState } from "@/components/empty-state";
import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { StatusBadge } from "@/components/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import type { SupportedMarket } from "../markets/types";
import { formatTimeframe } from "./format";
import { SignalFeedEntry } from "./signal-feed-entry";
import type {
  SignalConnectionStatus,
  SignalFeedEvent,
  SignalPreset,
} from "./types";

type SignalFeedProps = {
  events: SignalFeedEvent[];
  presets: SignalPreset[];
  markets: SupportedMarket[];
  marketFilter: string;
  presetFilter: string;
  onMarketFilterChange: (value: string) => void;
  onPresetFilterChange: (value: string) => void;
  isInitialLoading: boolean;
  isRefreshing: boolean;
  isLoadingMore: boolean;
  isStale: boolean;
  nextCursor: string | null;
  highlightedEventIds: Set<string>;
  connectionStatus: SignalConnectionStatus;
  announcement: string | null;
  error: string | null;
  soundPreferenceEnabled: boolean;
  soundSessionActive: boolean;
  soundError: string | null;
  soundAnnouncement: string | null;
  onActivateSound: () => void;
  onMuteSound: () => void;
  onRefresh: () => void;
  onLoadMore: () => void;
  onReconnect: () => void;
};

function connectionMessage(status: SignalConnectionStatus): string {
  switch (status) {
    case "connecting":
      return "Connecting to live signals…";
    case "live":
      return "Live updates connected.";
    case "reconnecting":
      return "Live updates interrupted. Reconnecting…";
    case "disconnected":
      return "Live updates are unavailable. History can still be refreshed.";
    case "history recovery required":
      return "Live history recovery is required. Refreshing…";
    case "authentication expired":
      return "Your session has ended. Please sign in again.";
  }
}

function connectionLabel(status: SignalConnectionStatus): string {
  switch (status) {
    case "live":
      return "Live";
    case "connecting":
      return "Connecting";
    case "reconnecting":
      return "Reconnecting";
    case "disconnected":
      return "Disconnected";
    case "history recovery required":
      return "Recovery required";
    case "authentication expired":
      return "Authentication expired";
  }
}

function presetFilterValue(preset: SignalPreset): string {
  return `${preset.code}:${preset.version}`;
}

export function SignalFeed({
  events,
  presets,
  markets,
  marketFilter,
  presetFilter,
  onMarketFilterChange,
  onPresetFilterChange,
  isInitialLoading,
  isRefreshing,
  isLoadingMore,
  isStale,
  nextCursor,
  highlightedEventIds,
  connectionStatus,
  announcement,
  error,
  soundPreferenceEnabled,
  soundSessionActive,
  soundError,
  soundAnnouncement,
  onActivateSound,
  onMuteSound,
  onRefresh,
  onLoadMore,
  onReconnect,
}: SignalFeedProps) {
  const filteredEvents = events.filter((event) => {
    const marketMatches = !marketFilter || event.market.symbol === marketFilter;
    const presetMatches =
      !presetFilter ||
      `${event.preset.code}:${event.preset.version}` === presetFilter;
    return marketMatches && presetMatches;
  });
  const availableMarkets = markets.filter(
    (market) =>
      market.status === "available" &&
      market.baseAsset &&
      market.quoteAsset,
  );

  return (
    <section aria-labelledby="signal-history-heading" className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2
            className="text-lg font-semibold outline-none"
            id="signal-history-heading"
            tabIndex={-1}
          >
            Signal history
          </h2>
          <p className="text-sm text-muted-foreground">
            Recent occurrences for signals you currently or previously subscribed
            to. Historical entries may predate your subscription.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={connectionLabel(connectionStatus)} />
          <Button
            aria-busy={isRefreshing}
            disabled={isRefreshing}
            onClick={onRefresh}
            type="button"
            variant="outline"
          >
            {isRefreshing ? "Refreshing…" : "Refresh"}
          </Button>
          {connectionStatus === "disconnected" ? (
            <Button onClick={onReconnect} type="button" variant="outline">
              Reconnect
            </Button>
          ) : null}
        </div>
      </div>

      <div aria-live="polite" className="space-y-1 text-sm">
        <p>{connectionMessage(connectionStatus)}</p>
        {announcement ? <p>{announcement}</p> : null}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="signal-feed-market-filter">
            Market filter
          </label>
          <Select
            onValueChange={(value) =>
              onMarketFilterChange(value === "__all__" ? "" : value)
            }
            value={marketFilter || "__all__"}
          >
            <SelectTrigger className="w-full" id="signal-feed-market-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All subscribed signals</SelectItem>
              {availableMarkets.map((market) => (
                <SelectItem key={market.symbol} value={market.symbol}>
                  {market.baseAsset}/{market.quoteAsset} ({market.symbol})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="signal-feed-preset-filter">
            Preset filter
          </label>
          <Select
            onValueChange={(value) =>
              onPresetFilterChange(value === "__all__" ? "" : value)
            }
            value={presetFilter || "__all__"}
          >
            <SelectTrigger className="w-full" id="signal-feed-preset-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All presets</SelectItem>
              {presets.map((preset) => (
                <SelectItem key={presetFilterValue(preset)} value={presetFilterValue(preset)}>
                  {preset.name} · {formatTimeframe(preset.timeframe)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end">
          {!soundPreferenceEnabled ? (
            <Button onClick={onActivateSound} type="button" variant="outline">
              Enable sound
            </Button>
          ) : !soundSessionActive ? (
            <Button onClick={onActivateSound} type="button" variant="outline">
              Activate sound for this session
            </Button>
          ) : (
            <Button onClick={onMuteSound} type="button" variant="outline">
              Mute sound
            </Button>
          )}
        </div>
      </div>

      {soundError ? (
        <InlineError message={soundError} title="Sound is unavailable" />
      ) : null}
      {soundAnnouncement ? <p aria-live="polite">{soundAnnouncement}</p> : null}
      {isStale ? (
        <Alert>
          <AlertTitle>Signal history may be stale</AlertTitle>
          <AlertDescription>Refresh to request the latest history.</AlertDescription>
        </Alert>
      ) : null}
      {error ? (
        <InlineError
          message={error}
          retryAction={<InlineErrorRetryButton onRetry={onRefresh} disabled={isRefreshing} />}
          title="Signal history could not be loaded"
        />
      ) : null}

      {isInitialLoading ? (
        <div aria-busy="true" aria-label="Loading signal history" role="status">
          <div className="space-y-3">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      ) : null}
      {!isInitialLoading && !filteredEvents.length ? (
        <EmptyState
          description={
            events.length
              ? "No signal history matches these filters."
              : "No signal history is available for your current or previous subscriptions yet."
          }
          title={events.length ? "No matching signal history" : "No signal history yet"}
        />
      ) : null}
      {filteredEvents.length ? (
        <div className="space-y-3" role="list">
          {filteredEvents.map((event) => (
            <div key={event.id} role="listitem">
              <SignalFeedEntry
                event={event}
                isHighlighted={highlightedEventIds.has(event.id)}
              />
            </div>
          ))}
        </div>
      ) : null}
      {nextCursor ? (
        <Button
          aria-busy={isLoadingMore}
          disabled={isLoadingMore}
          onClick={onLoadMore}
          type="button"
          variant="outline"
        >
          {isLoadingMore ? "Loading…" : "Load more"}
        </Button>
      ) : null}
    </section>
  );
}
