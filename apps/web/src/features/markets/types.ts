export type MarketPriceRules = {
  min: string;
  max: string;
  tick: string;
};

export type SupportedMarket = {
  exchange: "binance";
  marketType: "spot";
  symbol: string;
  baseAsset: string | null;
  quoteAsset: string | null;
  status: "available" | "unavailable";
  priceRules: MarketPriceRules | null;
  metadataCheckedAt: string | null;
};

export type SupportedMarketsEnvelope = {
  markets: SupportedMarket[];
};
