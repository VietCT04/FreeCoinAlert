"use client";

import { useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatExactDecimal } from "@/lib/decimal";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "@/components/status-badge";

import type { SupportedMarket } from "../markets/types";
import type { TelegramConnection } from "../telegram/types";
import type { CreatePriceAlertRequest, PriceAlertDirection } from "./types";

type PriceAlertFormProps = {
  connection: TelegramConnection | null;
  isCreating: boolean;
  markets: SupportedMarket[];
  onCreate: (request: CreatePriceAlertRequest) => Promise<boolean>;
  onCreated?: () => void;
};

function validateTarget(target: string): string | null {
  if (!target) return "Enter a target price.";
  if (target.length > 64) return "Target prices can contain at most 64 characters.";
  if (!/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(target)) {
    return "Enter a plain positive decimal price.";
  }
  const [whole, fraction = ""] = target.split(".");
  if (fraction.length > 18) return "Enter no more than 18 decimal places.";
  if (whole === "0" && !/[1-9]/.test(fraction)) {
    return "Enter a positive target price.";
  }
  return null;
}

function telegramStatusLabel(status: TelegramConnection["status"] | undefined): string {
  switch (status) {
    case "connected":
      return "Ready";
    case "linking":
      return "Linking";
    case "degraded":
      return "Needs attention";
    case "disconnected":
    case "not_connected":
    default:
      return "Not connected";
  }
}

export function PriceAlertForm({
  connection,
  isCreating,
  markets,
  onCreate,
  onCreated,
}: PriceAlertFormProps) {
  const availableMarkets = markets.filter(
    (market) =>
      market.status === "available" &&
      market.priceRules &&
      market.baseAsset &&
      market.quoteAsset,
  );
  const [marketSymbol, setMarketSymbol] = useState("");
  const [direction, setDirection] = useState<PriceAlertDirection>("cross_above");
  const [targetPrice, setTargetPrice] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const selectedMarket = useMemo(
    () => availableMarkets.find((market) => market.symbol === marketSymbol) ?? null,
    [availableMarkets, marketSymbol],
  );
  const targetError = validateTarget(targetPrice);
  const displayTargetPrice = formatExactDecimal(targetPrice);
  const telegramReady = connection?.status === "connected";
  const canSubmit = Boolean(
    selectedMarket &&
      telegramReady &&
      !targetError &&
      !isCreating,
  );

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
    if (created) {
      setMarketSymbol("");
      setDirection("cross_above");
      setTargetPrice("");
      setSubmitted(false);
      onCreated?.();
    }
  }

  const readiness = telegramStatusLabel(connection?.status);

  return (
    <form className="space-y-5" onSubmit={(event) => void handleSubmit(event)}>
      <div className="space-y-2">
        <Label htmlFor="price-alert-market">Market</Label>
        <Select onValueChange={setMarketSymbol} value={marketSymbol}>
          <SelectTrigger className="w-full" id="price-alert-market">
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
      </div>

      <div className="space-y-2">
        <Label htmlFor="price-alert-direction">Condition</Label>
        <Select
          onValueChange={(value) => setDirection(value as PriceAlertDirection)}
          value={direction}
        >
          <SelectTrigger className="w-full" id="price-alert-direction">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="cross_above">Crosses above</SelectItem>
            <SelectItem value="cross_below">Crosses below</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-sm text-muted-foreground">
          The first live price initializes the alert. A notification is sent only
          after a later crossing.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="price-alert-target">Target price</Label>
        <Input
          aria-describedby="price-alert-target-help price-alert-target-error"
          id="price-alert-target"
          inputMode="decimal"
          maxLength={64}
          onChange={(event) => setTargetPrice(event.target.value)}
          type="text"
          value={targetPrice}
        />
        {selectedMarket?.priceRules ? (
          <p className="text-sm text-muted-foreground" id="price-alert-target-help">
            Minimum: {formatExactDecimal(selectedMarket.priceRules.min)} · Maximum: {" "}
            {formatExactDecimal(selectedMarket.priceRules.max)} · Price step: {" "}
            {formatExactDecimal(selectedMarket.priceRules.tick)}
          </p>
        ) : null}
        {submitted && targetError ? (
          <p
            aria-live="assertive"
            className="text-sm text-destructive"
            id="price-alert-target-error"
          >
            {targetError}
          </p>
        ) : null}
      </div>

      <div className="flex items-center justify-between gap-3 rounded-lg border p-3">
        <div>
          <p className="text-sm font-medium">Telegram readiness</p>
          <p className="text-sm text-muted-foreground">
            A connected private Telegram destination is required.
          </p>
        </div>
        <StatusBadge status={readiness} />
      </div>

      {connection?.status !== "connected" ? (
        <Alert>
          <AlertTitle>Connect Telegram before creating an alert</AlertTitle>
          <AlertDescription>
            Price alerts are delivered through your private Telegram destination.
          </AlertDescription>
        </Alert>
      ) : null}

      {selectedMarket && targetPrice && !targetError ? (
        <Alert>
          <AlertTitle>Request preview</AlertTitle>
          <AlertDescription>
            Notify me in Telegram when {selectedMarket.symbol} crosses{" "}
            {direction === "cross_above" ? "above" : "below"} {displayTargetPrice}{" "}
            {selectedMarket.quoteAsset}.
          </AlertDescription>
        </Alert>
      ) : null}

      <Button aria-busy={isCreating} disabled={!canSubmit} type="submit">
        {isCreating ? "Creating price alert…" : "Create price alert"}
      </Button>
    </form>
  );
}
