"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { InlineError, InlineErrorRetryButton } from "@/components/inline-error";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { useAuth } from "../auth/auth-provider";
import { useMarkets } from "../markets/use-markets";
import { getSignalPresets } from "./api";
import { signalErrorMessage, isSignalAuthenticationError } from "./errors";
import { PresetCatalog } from "./preset-catalog";
import type {
  PresetSubscriptionFilter,
  PresetTimeframeFilter,
} from "./preset-catalog";
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
  const [timeframeFilter, setTimeframeFilter] =
    useState<PresetTimeframeFilter>("all");
  const [subscriptionFilter, setSubscriptionFilter] =
    useState<PresetSubscriptionFilter>("all");
  const [activeTab, setActiveTab] = useState("presets");
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
      setTimeframeFilter("all");
      setSubscriptionFilter("all");
      setActiveTab("presets");
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
    async (symbol: string, preset: SignalPreset) => {
      if (await subscriptions.subscribe(symbol, preset)) {
        toast.success("Signal subscription saved.");
      }
    },
    [subscriptions.subscribe],
  );
  const onSubscriptionConfirmDisable = useCallback(
    async (subscription: SignalSubscription) => {
      if (await subscriptions.disable(subscription)) {
        toast.success("Signal subscription disabled.");
      }
    },
    [subscriptions.disable],
  );
  const onSetTelegramDelivery = useCallback(
    async (subscription: SignalSubscription, enabled: boolean) => {
      if (await subscriptions.setTelegramDelivery(subscription, enabled)) {
        toast.success(
          enabled ? "Telegram delivery enabled." : "Telegram delivery disabled.",
        );
      }
    },
    [subscriptions.setTelegramDelivery],
  );

  const handleViewHistory = useCallback((preset: SignalPreset) => {
    setPresetFilter(`${preset.code}:${preset.version}`);
    setActiveTab("history");
    window.requestAnimationFrame(() => {
      document.getElementById("signal-history-heading")?.focus();
    });
  }, []);

  if (status !== "authenticated") {
    return null;
  }

  return (
    <section
      aria-label="Preset subscriptions and signal history"
      className="space-y-6"
    >
      {subscriptions.announcement ? (
        <p aria-live="polite">{subscriptions.announcement}</p>
      ) : null}
      {subscriptions.error ? (
        <InlineError
          message={subscriptions.error}
          retryAction={
            <InlineErrorRetryButton onRetry={() => void subscriptions.refresh()} />
          }
          title="Subscription update failed"
        />
      ) : null}
      <Tabs onValueChange={setActiveTab} value={activeTab}>
        <TabsList aria-label="Preset signal sections" variant="line">
          <TabsTrigger value="presets">Presets</TabsTrigger>
          <TabsTrigger value="history">Signal history</TabsTrigger>
        </TabsList>
        <TabsContent
          className="data-[state=inactive]:hidden"
          forceMount
          value="presets"
        >
          <PresetCatalog
            confirmingDisableId={subscriptions.confirmingDisableId}
            confirmingTelegramDeliveryId={subscriptions.confirmingTelegramDeliveryId}
            isMarketsLoading={markets.isLoading}
            isPresetsLoading={isPresetsLoading || subscriptions.isLoading}
            marketError={markets.error}
            markets={markets.markets}
            onAskToDisable={subscriptions.askToDisable}
            onAskToEnableTelegramDelivery={
              subscriptions.askToEnableTelegramDelivery
            }
            onCancelDisable={subscriptions.cancelDisable}
            onCancelTelegramDeliveryConfirmation={
              subscriptions.cancelTelegramDeliveryConfirmation
            }
            onConfirmDisable={onSubscriptionConfirmDisable}
            onRetryMarkets={() => void markets.refreshMarkets()}
            onSelectSymbol={setSelectedSymbol}
            onSetTelegramDelivery={onSetTelegramDelivery}
            onSubscribe={onSubscriptionSubscribe}
            onSubscriptionFilterChange={setSubscriptionFilter}
            onTimeframeFilterChange={setTimeframeFilter}
            onViewHistory={handleViewHistory}
            pendingKeys={subscriptions.pendingKeys}
            pendingTelegramDeliveryIds={subscriptions.pendingTelegramDeliveryIds}
            presetError={presetError}
            presets={presets}
            selectedSymbol={selectedSymbol}
            subscriptionFilter={subscriptionFilter}
            subscriptions={subscriptions.subscriptions}
            timeframeFilter={timeframeFilter}
          />
        </TabsContent>
        <TabsContent
          className="data-[state=inactive]:hidden"
          forceMount
          value="history"
        >
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
        </TabsContent>
      </Tabs>
    </section>
  );
}
