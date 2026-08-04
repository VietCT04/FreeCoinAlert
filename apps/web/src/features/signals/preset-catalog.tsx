"use client";

import { EmptyState } from "@/components/empty-state";
import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
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
import { PresetCard } from "./preset-card";
import type { SignalPreset, SignalSubscription } from "./types";

export type PresetTimeframeFilter = "all" | "1h" | "4h";
export type PresetSubscriptionFilter = "all" | "subscribed" | "not_subscribed";

type PresetCatalogProps = {
  markets: SupportedMarket[];
  marketError: string | null;
  isMarketsLoading: boolean;
  presets: SignalPreset[];
  presetError: string | null;
  isPresetsLoading: boolean;
  subscriptions: SignalSubscription[];
  selectedSymbol: string;
  timeframeFilter: PresetTimeframeFilter;
  subscriptionFilter: PresetSubscriptionFilter;
  onSelectSymbol: (symbol: string) => void;
  onTimeframeFilterChange: (value: PresetTimeframeFilter) => void;
  onSubscriptionFilterChange: (value: PresetSubscriptionFilter) => void;
  pendingKeys: Set<string>;
  confirmingDisableId: string | null;
  onSubscribe: (symbol: string, preset: SignalPreset) => void;
  onAskToDisable: (subscriptionId: string) => void;
  onCancelDisable: () => void;
  onConfirmDisable: (subscription: SignalSubscription) => void;
  pendingTelegramDeliveryIds: Set<string>;
  confirmingTelegramDeliveryId: string | null;
  onAskToEnableTelegramDelivery: (subscriptionId: string) => void;
  onCancelTelegramDeliveryConfirmation: () => void;
  onSetTelegramDelivery: (
    subscription: SignalSubscription,
    enabled: boolean,
  ) => void;
  onViewHistory: (preset: SignalPreset) => void;
  onRetryMarkets: () => void;
};

function cardKey(symbol: string, preset: SignalPreset): string {
  return `${symbol}:${preset.code}:${preset.version}`;
}

export function PresetCatalog({
  markets,
  marketError,
  isMarketsLoading,
  presets,
  presetError,
  isPresetsLoading,
  subscriptions,
  selectedSymbol,
  timeframeFilter,
  subscriptionFilter,
  onSelectSymbol,
  onTimeframeFilterChange,
  onSubscriptionFilterChange,
  pendingKeys,
  confirmingDisableId,
  onSubscribe,
  onAskToDisable,
  onCancelDisable,
  onConfirmDisable,
  pendingTelegramDeliveryIds,
  confirmingTelegramDeliveryId,
  onAskToEnableTelegramDelivery,
  onCancelTelegramDeliveryConfirmation,
  onSetTelegramDelivery,
  onViewHistory,
  onRetryMarkets,
}: PresetCatalogProps) {
  const availableMarkets = markets.filter(
    (market) =>
      market.status === "available" &&
      market.baseAsset !== null &&
      market.quoteAsset !== null,
  );
  const selectedMarket = availableMarkets.find(
    (market) => market.symbol === selectedSymbol,
  );
  const timeframes: Array<"1h" | "4h"> = ["1h", "4h"];

  const filteredPresets = presets.filter((preset) => {
    if (timeframeFilter !== "all" && preset.timeframe !== timeframeFilter) {
      return false;
    }
    if (!selectedMarket) return false;
    const subscription = subscriptions.find(
      (item) =>
        item.market.symbol === selectedMarket.symbol &&
        item.preset.code === preset.code &&
        item.preset.version === preset.version,
    );
    if (subscriptionFilter === "subscribed") {
      return subscription?.status === "active";
    }
    if (subscriptionFilter === "not_subscribed") {
      return subscription?.status !== "active";
    }
    return true;
  });

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="signal-market">
            Market
          </label>
          {availableMarkets.length ? (
            <Select onValueChange={onSelectSymbol} value={selectedSymbol}>
              <SelectTrigger className="w-full" id="signal-market">
                <SelectValue placeholder="Select a supported market" />
              </SelectTrigger>
              <SelectContent>
                {availableMarkets.map((market) => (
                  <SelectItem key={market.symbol} value={market.symbol}>
                    {market.baseAsset}/{market.quoteAsset} ({market.symbol})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="signal-timeframe-filter">
            Timeframe
          </label>
          <Select
            onValueChange={(value) =>
              onTimeframeFilterChange(value as PresetTimeframeFilter)
            }
            value={timeframeFilter}
          >
            <SelectTrigger className="w-full" id="signal-timeframe-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All timeframes</SelectItem>
              <SelectItem value="1h">1 hour</SelectItem>
              <SelectItem value="4h">4 hours</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium" htmlFor="signal-subscription-filter">
            Subscription
          </label>
          <Select
            onValueChange={(value) =>
              onSubscriptionFilterChange(value as PresetSubscriptionFilter)
            }
            value={subscriptionFilter}
          >
            <SelectTrigger className="w-full" id="signal-subscription-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All presets</SelectItem>
              <SelectItem value="subscribed">Subscribed</SelectItem>
              <SelectItem value="not_subscribed">Not subscribed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isMarketsLoading ? (
        <div aria-busy="true" aria-label="Loading supported markets" role="status">
          <Skeleton className="h-8 w-full" />
        </div>
      ) : null}
      {marketError ? (
        <InlineError
          message="Preset signals are temporarily unavailable because market information is not ready."
          retryAction={<InlineErrorRetryButton onRetry={onRetryMarkets} />}
          title="Market catalogue unavailable"
        />
      ) : null}
      {!isMarketsLoading && !marketError && !availableMarkets.length ? (
        <EmptyState
          description="No supported market is currently ready for preset subscriptions."
          title="Preset signals are unavailable"
        />
      ) : null}

      {isPresetsLoading ? (
        <div aria-busy="true" aria-label="Loading preset signals" role="status">
          <div className="grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-72 w-full" />
            <Skeleton className="h-72 w-full" />
          </div>
        </div>
      ) : null}
      {presetError ? (
        <InlineError message={presetError} title="Preset catalogue unavailable" />
      ) : null}
      {!isPresetsLoading && !presetError && !presets.length ? (
        <EmptyState
          description="The fixed preset catalogue is not available right now."
          title="No preset signals available"
        />
      ) : null}

      {!isPresetsLoading && !presetError && selectedMarket && presets.length ? (
        filteredPresets.length ? (
          <div className="space-y-6">
            {timeframes.map((timeframe) => {
              const timeframePresets = filteredPresets.filter(
                (preset) => preset.timeframe === timeframe,
              );
              if (!timeframePresets.length) return null;
              return (
                <section aria-labelledby={`preset-${timeframe}-heading`} key={timeframe}>
                  <h3 className="mb-3 text-lg font-semibold" id={`preset-${timeframe}-heading`}>
                    {formatTimeframe(timeframe)} presets
                  </h3>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {timeframePresets.map((preset) => {
                      const subscription = subscriptions.find(
                        (item) =>
                          item.market.symbol === selectedMarket.symbol &&
                          item.preset.code === preset.code &&
                          item.preset.version === preset.version,
                      );
                      const key = cardKey(selectedMarket.symbol, preset);
                      return (
                        <PresetCard
                          isConfirmingDisable={confirmingDisableId === subscription?.id}
                          isPending={pendingKeys.has(key)}
                          isTelegramDeliveryPending={pendingTelegramDeliveryIds.has(
                            subscription?.id ?? "",
                          )}
                          isConfirmingTelegramDelivery={
                            confirmingTelegramDeliveryId === subscription?.id
                          }
                          key={key}
                          marketSymbol={selectedMarket.symbol}
                          onAskToDisable={() => {
                            if (subscription) onAskToDisable(subscription.id);
                          }}
                          onCancelDisable={onCancelDisable}
                          onConfirmDisable={() => {
                            if (subscription) onConfirmDisable(subscription);
                          }}
                          onAskToEnableTelegramDelivery={() => {
                            if (subscription) {
                              onAskToEnableTelegramDelivery(subscription.id);
                            }
                          }}
                          onCancelTelegramDeliveryConfirmation={
                            onCancelTelegramDeliveryConfirmation
                          }
                          onSetTelegramDelivery={(enabled) => {
                            if (subscription) {
                              onSetTelegramDelivery(subscription, enabled);
                            }
                          }}
                          onSubscribe={() => onSubscribe(selectedMarket.symbol, preset)}
                          onViewHistory={() => onViewHistory(preset)}
                          preset={preset}
                          subscription={subscription}
                        />
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        ) : (
          <EmptyState
            description="Try another timeframe, market, or subscription filter."
            title="No presets match these filters"
          />
        )
      ) : null}
    </div>
  );
}
