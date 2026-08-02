"use client";

import type { SupportedMarket } from "../markets/types";
import {
  formatTimeframe,
} from "./format";
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
    (market) => market.status === "available" && market.baseAsset && market.quoteAsset,
  );

  return (
    <section aria-labelledby="signal-history-heading" className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold" id="signal-history-heading">
            Signal history
          </h3>
          <p className="text-sm text-zinc-600 dark:text-zinc-300">
            Recent occurrences for signals you currently or previously subscribed
            to. Historical entries may predate your subscription.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
            aria-busy={isRefreshing}
            disabled={isRefreshing}
            onClick={onRefresh}
            type="button"
          >
            {isRefreshing ? "Refreshing…" : "Refresh history"}
          </button>
          {connectionStatus === "disconnected" ? (
            <button
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700"
              onClick={onReconnect}
              type="button"
            >
              Reconnect live updates
            </button>
          ) : null}
        </div>
      </div>

      <div aria-live="polite" className="space-y-1 text-sm">
        <p>{connectionMessage(connectionStatus)}</p>
        {announcement ? <p>{announcement}</p> : null}
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-48 flex-1 space-y-1">
          <label className="text-sm font-medium" htmlFor="signal-feed-market-filter">
            Market filter
          </label>
          <select
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
            id="signal-feed-market-filter"
            onChange={(event) => onMarketFilterChange(event.target.value)}
            value={marketFilter}
          >
            <option value="">All subscribed signals</option>
            {availableMarkets.map((market) => (
              <option key={market.symbol} value={market.symbol}>
                {market.baseAsset}/{market.quoteAsset} ({market.symbol})
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-48 flex-1 space-y-1">
          <label className="text-sm font-medium" htmlFor="signal-feed-preset-filter">
            Preset filter
          </label>
          <select
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
            id="signal-feed-preset-filter"
            onChange={(event) => onPresetFilterChange(event.target.value)}
            value={presetFilter}
          >
            <option value="">All presets</option>
            {presets.map((preset) => (
              <option key={presetFilterValue(preset)} value={presetFilterValue(preset)}>
                {preset.name} · {formatTimeframe(preset.timeframe)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          {!soundPreferenceEnabled ? (
            <button
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700"
              onClick={onActivateSound}
              type="button"
            >
              Enable sound
            </button>
          ) : !soundSessionActive ? (
            <button
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700"
              onClick={onActivateSound}
              type="button"
            >
              Activate sound for this session
            </button>
          ) : (
            <button
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700"
              onClick={onMuteSound}
              type="button"
            >
              Mute sound
            </button>
          )}
        </div>
      </div>
      {soundError ? (
        <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">
          {soundError}
        </p>
      ) : null}
      {soundAnnouncement ? <p aria-live="polite">{soundAnnouncement}</p> : null}

      {isInitialLoading ? (
        <p aria-live="polite">Loading signal history…</p>
      ) : null}
      {isStale ? (
        <p>
          Signal history may be stale. Refresh to try again.
        </p>
      ) : null}
      {error ? (
        <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      ) : null}
      {!isInitialLoading && !filteredEvents.length ? (
        <p>
          {events.length
            ? "No signal history matches these filters."
            : "No signal history for your current or previous signal subscriptions yet."}
        </p>
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
        <button
          className="rounded-lg border border-zinc-300 px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60 dark:border-zinc-700"
          aria-busy={isLoadingMore}
          disabled={isLoadingMore}
          onClick={onLoadMore}
          type="button"
        >
          {isLoadingMore ? "Loading…" : "Load more"}
        </button>
      ) : null}
    </section>
  );
}
