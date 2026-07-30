"use client";

import { useMemo, useState } from "react";

import type { SupportedMarket } from "../markets/types";
import type { TelegramConnection } from "../telegram/types";
import type { CreatePriceAlertRequest, PriceAlertDirection } from "./types";

type PriceAlertFormProps = {
  connection: TelegramConnection | null;
  isCreating: boolean;
  markets: SupportedMarket[];
  onCreate: (request: CreatePriceAlertRequest) => Promise<boolean>;
};

function validateTarget(target: string): string | null {
  if (!target) return "Enter a target price.";
  if (target.length > 64) return "Target prices can contain at most 64 characters.";
  if (!/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(target)) return "Enter a plain positive decimal price.";
  const [whole, fraction = ""] = target.split(".");
  if (fraction.length > 18) return "Enter no more than 18 decimal places.";
  if (whole === "0" && !/[1-9]/.test(fraction)) return "Enter a positive target price.";
  return null;
}

export function PriceAlertForm({ connection, isCreating, markets, onCreate }: PriceAlertFormProps) {
  const availableMarkets = markets.filter((market) => market.status === "available" && market.priceRules);
  const [marketSymbol, setMarketSymbol] = useState("");
  const [direction, setDirection] = useState<PriceAlertDirection>("cross_above");
  const [targetPrice, setTargetPrice] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const selectedMarket = useMemo(() => availableMarkets.find((market) => market.symbol === marketSymbol) ?? null, [availableMarkets, marketSymbol]);
  const targetError = validateTarget(targetPrice);
  const telegramReady = connection?.status === "connected";
  const canSubmit = Boolean(selectedMarket && telegramReady && !targetError && !isCreating);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
    if (!selectedMarket || targetError || !telegramReady) return;
    const created = await onCreate({
      exchange: selectedMarket.exchange,
      marketType: selectedMarket.marketType,
      symbol: selectedMarket.symbol,
      direction,
      targetPrice,
    });
    if (created) { setTargetPrice(""); setSubmitted(false); }
  }

  return (
    <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
      <div className="space-y-1">
        <label className="font-medium" htmlFor="price-alert-market">Market</label>
        <select className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950" id="price-alert-market" onChange={(event) => setMarketSymbol(event.target.value)} value={marketSymbol}>
          <option value="">Select a supported market</option>
          {availableMarkets.map((market) => <option key={market.symbol} value={market.symbol}>{market.baseAsset}/{market.quoteAsset} ({market.symbol})</option>)}
        </select>
      </div>
      <div className="space-y-1">
        <label className="font-medium" htmlFor="price-alert-direction">Direction</label>
        <select className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950" id="price-alert-direction" onChange={(event) => setDirection(event.target.value as PriceAlertDirection)} value={direction}>
          <option value="cross_above">Crosses above</option>
          <option value="cross_below">Crosses below</option>
        </select>
        <p className="text-sm text-zinc-600 dark:text-zinc-300">The first live price initializes the alert. A notification is sent only after a later crossing.</p>
      </div>
      <div className="space-y-1">
        <label className="font-medium" htmlFor="price-alert-target">Target price</label>
        <input aria-describedby="price-alert-target-help price-alert-target-error" className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950" id="price-alert-target" inputMode="decimal" maxLength={64} onChange={(event) => setTargetPrice(event.target.value)} type="text" value={targetPrice} />
        {selectedMarket?.priceRules ? <p className="text-sm text-zinc-600 dark:text-zinc-300" id="price-alert-target-help">Minimum: {selectedMarket.priceRules.min} · Maximum: {selectedMarket.priceRules.max} · Price step: {selectedMarket.priceRules.tick}</p> : null}
        {submitted && targetError ? <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300" id="price-alert-target-error">{targetError}</p> : null}
      </div>
      {connection?.status !== "connected" ? <p className="text-sm text-zinc-600 dark:text-zinc-300">{connection?.status === "degraded" ? "Reconnect Telegram before creating new price alerts." : "Connect Telegram before creating a price alert."} <a className="underline" href="#telegram-connection">Go to Telegram notifications.</a></p> : null}
      {selectedMarket && targetPrice && !targetError ? <p className="rounded-lg bg-zinc-100 p-3 text-sm dark:bg-zinc-800">Notify me in Telegram when {selectedMarket.symbol} crosses {direction === "cross_above" ? "above" : "below"} {targetPrice} {selectedMarket.quoteAsset}.</p> : null}
      <button className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900" disabled={!canSubmit} type="submit">{isCreating ? "Creating price alert…" : "Create price alert"}</button>
    </form>
  );
}
