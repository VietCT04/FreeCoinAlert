"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "../auth/auth-provider";
import { useMarkets } from "../markets/use-markets";
import { getSignalPresets } from "./api";
import { signalErrorMessage, isSignalAuthenticationError } from "./errors";
import { PresetCatalog } from "./preset-catalog";
import { SignalFeed } from "./signal-feed";
import type {
  SignalFeedEvent,
  SignalPreset,
  SignalSubscription,
} from "./types";
import { useSignalFeed } from "./use-signal-feed";
import { useSignalSound } from "./use-signal-sound";
import { useSignalStream } from "./use-signal-stream";
import { useSignalSubscriptions } from "./use-signal-subscriptions";

export function PresetSignalPanel() {
  const { csrfToken, refreshSession, status } = useAuth();
  const markets = useMarkets(status);
  const sound = useSignalSound(status);
  const [presets, setPresets] = useState<SignalPreset[]>([]);
  const [presetError, setPresetError] = useState<string | null>(null);
  const [isPresetsLoading, setIsPresetsLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [marketFilter, setMarketFilter] = useState("");
  const [presetFilter, setPresetFilter] = useState("");
  const [streamRestartToken, setStreamRestartToken] = useState(0);

  const handleNewLiveSignal = useCallback(
    (_event: SignalFeedEvent) => {
      void sound.playLivePip();
    },
    [sound.playLivePip],
  );
  const feed = useSignalFeed({
    authStatus: status,
    onNewLiveSignal: handleNewLiveSignal,
    refreshSession,
  });
  const handleSubscriptionChanged = useCallback(async () => {
    const refreshed = await feed.refreshFirstPage();
    if (refreshed) {
      setStreamRestartToken((current) => current + 1);
    }
  }, [feed.refreshFirstPage]);
  const subscriptions = useSignalSubscriptions({
    authStatus: status,
    csrfToken,
    onSubscriptionChanged: handleSubscriptionChanged,
    refreshSession,
  });
  const recoverHistory = useCallback(async (): Promise<boolean> => {
    const [feedRecovered, subscriptionsRecovered] = await Promise.all([
      feed.refreshFirstPage(),
      subscriptions.refresh(),
    ]);
    return feedRecovered && subscriptionsRecovered;
  }, [feed.refreshFirstPage, subscriptions.refresh]);
  const handleStreamInvalidation = useCallback(
    (event: Parameters<typeof feed.applyStreamInvalidation>[0]) =>
      feed.applyStreamInvalidation(event),
    [feed.applyStreamInvalidation],
  );
  const stream = useSignalStream({
    authStatus: status,
    enabled: feed.baselineReady,
    onAuthExpired: () => void refreshSession(),
    onInvalidation: handleStreamInvalidation,
    onSignal: feed.applyStreamSignal,
    recoverHistory,
    restartToken: streamRestartToken,
    streamCursor: feed.streamCursor,
  });

  useEffect(() => {
    if (status !== "authenticated") {
      setPresets([]);
      setPresetError(null);
      setIsPresetsLoading(false);
      setSelectedSymbol("");
      setMarketFilter("");
      setPresetFilter("");
      return;
    }

    let isCurrent = true;
    setIsPresetsLoading(true);
    setPresetError(null);
    void getSignalPresets()
      .then((response) => {
        if (isCurrent) {
          setPresets(response.presets);
        }
      })
      .catch(async (requestError: unknown) => {
        if (!isCurrent) {
          return;
        }
        if (isSignalAuthenticationError(requestError)) {
          await refreshSession();
        }
        setPresetError(signalErrorMessage(requestError));
      })
      .finally(() => {
        if (isCurrent) {
          setIsPresetsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [refreshSession, status]);

  useEffect(() => {
    const availableMarkets = markets.markets.filter(
      (market) =>
        market.status === "available" &&
        market.baseAsset !== null &&
        market.quoteAsset !== null,
    );
    if (!availableMarkets.length) {
      setSelectedSymbol("");
      return;
    }
    if (!availableMarkets.some((market) => market.symbol === selectedSymbol)) {
      setSelectedSymbol(availableMarkets[0].symbol);
    }
  }, [markets.markets, selectedSymbol]);

  const onSubscriptionSubscribe = useCallback(
    (symbol: string, preset: SignalPreset) => {
      void subscriptions.subscribe(symbol, preset);
    },
    [subscriptions.subscribe],
  );
  const onSubscriptionConfirmDisable = useCallback(
    (subscription: SignalSubscription) => {
      void subscriptions.disable(subscription);
    },
    [subscriptions.disable],
  );
  const onSetTelegramDelivery = useCallback(
    (subscription: SignalSubscription, enabled: boolean) => {
      void subscriptions.setTelegramDelivery(subscription, enabled);
    },
    [subscriptions.setTelegramDelivery],
  );

  if (status !== "authenticated") {
    return null;
  }

  return (
    <section
      aria-labelledby="preset-signals-heading"
      className="space-y-6 rounded-xl border border-zinc-200 p-5 dark:border-zinc-700"
    >
      <div>
        <h2 className="text-xl font-semibold" id="preset-signals-heading">
          Preset signals
        </h2>
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          Subscribe to fixed technical signals and review their recent history.
          These signals are informational and are not trading advice.
        </p>
      </div>
      <div aria-live="polite">
        {subscriptions.announcement ? <p>{subscriptions.announcement}</p> : null}
        {subscriptions.error ? <p>{subscriptions.error}</p> : null}
      </div>
      <PresetCatalog
        confirmingDisableId={subscriptions.confirmingDisableId}
        isMarketsLoading={markets.isLoading}
        isPresetsLoading={isPresetsLoading || subscriptions.isLoading}
        marketError={markets.error}
        markets={markets.markets}
        onAskToDisable={subscriptions.askToDisable}
        onCancelDisable={subscriptions.cancelDisable}
        onConfirmDisable={onSubscriptionConfirmDisable}
        onAskToEnableTelegramDelivery={
          subscriptions.askToEnableTelegramDelivery
        }
        onCancelTelegramDeliveryConfirmation={
          subscriptions.cancelTelegramDeliveryConfirmation
        }
        onSetTelegramDelivery={onSetTelegramDelivery}
        onRetryMarkets={() => void markets.refreshMarkets()}
        onSelectSymbol={setSelectedSymbol}
        onSubscribe={onSubscriptionSubscribe}
        onViewHistory={(preset) =>
          setPresetFilter(`${preset.code}:${preset.version}`)
        }
        pendingKeys={subscriptions.pendingKeys}
        pendingTelegramDeliveryIds={subscriptions.pendingTelegramDeliveryIds}
        presetError={presetError}
        presets={presets}
        selectedSymbol={selectedSymbol}
        subscriptions={subscriptions.subscriptions}
        confirmingTelegramDeliveryId={subscriptions.confirmingTelegramDeliveryId}
      />
      <SignalFeed
        announcement={feed.announcement}
        connectionStatus={stream.status}
        error={feed.error}
        events={feed.events}
        highlightedEventIds={feed.highlightedEventIds}
        isInitialLoading={feed.isInitialLoading}
        isLoadingMore={feed.isLoadingMore}
        isRefreshing={feed.isRefreshing}
        isStale={feed.isStale}
        marketFilter={marketFilter}
        markets={markets.markets}
        nextCursor={feed.nextCursor}
        onActivateSound={() => void sound.activate()}
        onLoadMore={() => void feed.loadMore()}
        onMarketFilterChange={setMarketFilter}
        onMuteSound={sound.mute}
        onPresetFilterChange={setPresetFilter}
        onReconnect={() => void stream.reconnect()}
        onRefresh={() => void recoverHistory()}
        presetFilter={presetFilter}
        presets={presets}
        soundAnnouncement={sound.announcement}
        soundError={sound.error}
        soundPreferenceEnabled={sound.preferenceEnabled}
        soundSessionActive={sound.sessionActive}
      />
    </section>
  );
}
