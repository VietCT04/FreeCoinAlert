export type SignalTimeframe = "1h" | "4h";
export type SignalDirection = "cross_above" | "cross_below";
export type SignalStrategyType = "price_sma_cross" | "rsi_threshold_cross";
export type SignalSubscriptionStatus = "active" | "disabled";
export type SignalFeedStatus = "current" | "invalidated";
export type SignalDeliveryMode = "live" | "replay";

export type SignalParameters = {
  period: number;
  threshold: string | null;
  priceInput: "close";
};

export type SignalPreset = {
  code: string;
  version: number;
  name: string;
  description: string;
  strategyType: SignalStrategyType;
  timeframe: SignalTimeframe;
  direction: SignalDirection;
  parameters: SignalParameters;
  status: "available";
};

export type SignalPresetEnvelope = {
  presets: SignalPreset[];
};

export type SignalMarket = {
  exchange: "binance";
  marketType: "spot";
  symbol: string;
  baseAsset: string;
  quoteAsset: string;
};

export type SignalSubscriptionPreset = {
  code: string;
  version: number;
  name: string;
  timeframe: SignalTimeframe;
  direction: SignalDirection;
  parameters: SignalParameters;
};

export type SignalTelegramDeliveryReadiness =
  | "ready"
  | "linking"
  | "not_connected"
  | "degraded";

export type SignalTelegramDelivery = {
  enabled: boolean;
  readiness: SignalTelegramDeliveryReadiness;
  statusReason: string | null;
  changedAt: string | null;
};

export type SignalSubscription = {
  id: string;
  status: SignalSubscriptionStatus;
  statusReason: string | null;
  market: SignalMarket;
  preset: SignalSubscriptionPreset;
  telegramDelivery: SignalTelegramDelivery;
  activatedAt: string;
  disabledAt: string | null;
};

export type SignalSubscriptionEnvelope = {
  subscription: SignalSubscription;
};

export type SignalSubscriptionListEnvelope = {
  subscriptions: SignalSubscription[];
};

export type EnableSignalSubscriptionRequest = {
  exchange: "binance";
  market_type: "spot";
  symbol: string;
  preset_code: string;
  preset_version: number;
};

export type SignalFeedComparison = {
  leftLabel: string;
  rightLabel: string;
  previousLeft: string;
  previousRight: string;
  currentLeft: string;
  currentRight: string;
};

export type SignalFeedCandle = {
  revision: number;
  closePrice: string;
  openTime: string;
  closeTime: string;
};

export type SignalFeedPreset = {
  code: string;
  version: number;
  name: string;
  strategyType: SignalStrategyType;
  timeframe: SignalTimeframe;
  direction: SignalDirection;
  parameters: SignalParameters;
};

export type SignalFeedEvent = {
  id: string;
  status: SignalFeedStatus;
  invalidationReason: string | null;
  market: SignalMarket;
  preset: SignalFeedPreset;
  comparison: SignalFeedComparison;
  candle: SignalFeedCandle;
  backfilled: boolean;
  occurredAt: string;
  recordedAt: string;
  deliveryMode?: SignalDeliveryMode;
};

export type SignalFeedEnvelope = {
  events: SignalFeedEvent[];
  nextCursor: string | null;
  streamCursor: string;
};

export type SignalInvalidationEvent = {
  eventId: string;
  reason: string;
  deliveryMode: SignalDeliveryMode;
};

export type SignalConnectionStatus =
  | "connecting"
  | "live"
  | "reconnecting"
  | "disconnected"
  | "history recovery required"
  | "authentication expired";
