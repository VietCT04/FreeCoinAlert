export type PriceAlertDirection = "cross_above" | "cross_below";
export type PriceAlertStatus = "active" | "triggered" | "disabled" | "failed";
export type PriceAlertDeliveryStatus =
  | "not_queued"
  | "queued"
  | "sending"
  | "retrying"
  | "sent"
  | "failed"
  | "outcome_unknown";
export type PriceAlertMarketDataStatus =
  | "live"
  | "stale"
  | "disconnected"
  | "unavailable";

export type PriceAlert = {
  id: string;
  type: "price_cross";
  market: {
    exchange: string;
    marketType: string;
    symbol: string;
    baseAsset: string;
    quoteAsset: string;
  };
  direction: PriceAlertDirection;
  targetPrice: string;
  status: PriceAlertStatus;
  statusReason: string | null;
  evaluationReady: boolean;
  lastObservedPrice: string | null;
  createdAt: string;
  trigger: { price: string; occurredAt: string } | null;
  delivery: {
    status: PriceAlertDeliveryStatus;
    sentAt: string | null;
    failureCode: string | null;
  };
  marketData: {
    status: PriceAlertMarketDataStatus;
    lastObservedAt: string | null;
  };
};

export type PriceAlertEnvelope = { alert: PriceAlert };
export type PriceAlertListEnvelope = { alerts: PriceAlert[]; nextCursor: string | null };

export type CreatePriceAlertRequest = {
  exchange: string;
  marketType: string;
  symbol: string;
  direction: PriceAlertDirection;
  targetPrice: string;
};
