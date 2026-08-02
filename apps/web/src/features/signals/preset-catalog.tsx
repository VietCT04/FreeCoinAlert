"use client";

import type { SupportedMarket } from "../markets/types";
import { formatTimeframe } from "./format";
import { PresetCard } from "./preset-card";
import type { SignalPreset, SignalSubscription } from "./types";

type PresetCatalogProps = {
  markets: SupportedMarket[];
  marketError: string | null;
  isMarketsLoading: boolean;
  presets: SignalPreset[];
  presetError: string | null;
  isPresetsLoading: boolean;
  subscriptions: SignalSubscription[];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  pendingKeys: Set<string>;
  confirmingDisableId: string | null;
  onSubscribe: (symbol: string, preset: SignalPreset) => void;
  onAskToDisable: (subscriptionId: string) => void;
  onCancelDisable: () => void;
  onConfirmDisable: (subscription: SignalSubscription) => void;
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
  onSelectSymbol,
  pendingKeys,
  confirmingDisableId,
  onSubscribe,
  onAskToDisable,
  onCancelDisable,
  onConfirmDisable,
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

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <label className="font-medium" htmlFor="signal-market">
          Market
        </label>
        {isMarketsLoading ? (
          <p aria-live="polite">Loading supported markets…</p>
        ) : null}
        {marketError ? (
          <div className="space-y-2">
            <p>
              Preset signals are temporarily unavailable because market
              information is not ready.
            </p>
            <button
              className="rounded-lg border border-zinc-300 px-3 py-2 dark:border-zinc-700"
              onClick={onRetryMarkets}
              type="button"
            >
              Retry markets
            </button>
          </div>
        ) : null}
        {!isMarketsLoading && !marketError && !availableMarkets.length ? (
          <p>
            Preset signals are temporarily unavailable because market
            information is not ready.
          </p>
        ) : null}
        {availableMarkets.length ? (
          <select
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
            id="signal-market"
            onChange={(event) => onSelectSymbol(event.target.value)}
            value={selectedSymbol}
          >
            {availableMarkets.map((market) => (
              <option key={market.symbol} value={market.symbol}>
                {market.baseAsset}/{market.quoteAsset} ({market.symbol})
              </option>
            ))}
          </select>
        ) : null}
      </div>

      {isPresetsLoading ? (
        <p aria-live="polite">Loading preset signals…</p>
      ) : null}
      {presetError ? <p>{presetError}</p> : null}
      {!isPresetsLoading && !presetError && !presets.length ? (
        <p>Preset signals are temporarily unavailable.</p>
      ) : null}

      {selectedMarket && presets.length ? (
        <div className="space-y-6">
          {timeframes.map((timeframe) => {
            const timeframePresets = presets.filter(
              (preset) => preset.timeframe === timeframe,
            );
            if (!timeframePresets.length) {
              return null;
            }
            return (
              <fieldset key={timeframe} className="space-y-3">
                <legend className="text-lg font-semibold">
                  {formatTimeframe(timeframe)}
                </legend>
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
                        isConfirmingDisable={
                          confirmingDisableId === subscription?.id
                        }
                        isPending={pendingKeys.has(key)}
                        key={key}
                        marketSymbol={selectedMarket.symbol}
                        onAskToDisable={() => {
                          if (subscription) {
                            onAskToDisable(subscription.id);
                          }
                        }}
                        onCancelDisable={onCancelDisable}
                        onConfirmDisable={() => {
                          if (subscription) {
                            onConfirmDisable(subscription);
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
              </fieldset>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
