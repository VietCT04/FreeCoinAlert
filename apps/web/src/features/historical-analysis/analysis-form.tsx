"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { InlineError } from "@/components/inline-error";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { createIdempotencyKey } from "@/lib/idempotency";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import type { SupportedMarket } from "../markets/types";
import { HistoricalAnalysisApiError } from "./api";
import { historicalAnalysisErrorMessage } from "./errors";
import {
  formatBasisPoints,
  formatDirection,
  formatStrategyType,
  formatTimeframe,
  getDefaultUtcDateRange,
  inclusiveDateRangeToApiRange,
  inclusiveRangeDays,
} from "./format";
import type {
  AvailableHistoricalPreset,
  HistoricalAnalysisConfiguration,
  HistoricalAnalysisCreateRequest,
  HistoricalAnalysisRun,
} from "./types";

type AnalysisFormProps = {
  configuration: HistoricalAnalysisConfiguration;
  isSubmitting: boolean;
  markets: SupportedMarket[];
  onSubmit: (
    request: HistoricalAnalysisCreateRequest,
    idempotencyKey: string,
  ) => Promise<HistoricalAnalysisRun>;
  presets: AvailableHistoricalPreset[];
};

function presetKey(preset: AvailableHistoricalPreset): string {
  return `${preset.code}:${preset.version}`;
}

function AssumptionsCard({
  configuration,
}: {
  configuration: HistoricalAnalysisConfiguration;
}) {
  const assumptions = configuration.assumptions;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assumptions</CardTitle>
        <CardDescription>
          These values are controlled by the server and apply to the entire
          hypothetical simulation.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <ul className="grid gap-2 sm:grid-cols-2">
          <li>Signal known at confirmed candle close</li>
          <li>Entry at the next candle open</li>
          <li>
            Close exit after {assumptions.holdingPeriodCandles} held candles
          </li>
          <li>Cross-above is long; cross-below is synthetic short</li>
          <li>Full hypothetical-equity sizing</li>
          <li>One position at a time</li>
          <li>Fees: {formatBasisPoints(assumptions.feeBpsPerSide)} per side</li>
          <li>
            Slippage: {formatBasisPoints(assumptions.slippageBpsPerSide)} per
            side
          </li>
          <li>Overlapping signals are ignored</li>
          <li>Incomplete forward windows are not opened</li>
        </ul>
        <p className="leading-6 text-muted-foreground">
          The server validates complete stored candle coverage and the required
          warm-up before running the fixed preset. Historical analysis does not
          contact Binance or create live work.
        </p>
        <Alert className="border-warning/50 bg-warning/10" variant="warning">
          <AlertTitle>Historical simulation safety boundary</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>
              Synthetic-short results are analytical inverse exposure. They are
              not executable Binance Spot trades and do not model borrowing,
              margin, leverage, liquidation, or derivatives.
            </p>
            <p>
              This is a historical hypothetical simulation using stored candle
              data and fixed assumptions. It is not financial advice, a
              prediction, or a guarantee of future results. Real execution,
              liquidity, fees, slippage, and market behavior may differ.
            </p>
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}

function validateDateRange(
  startDate: string,
  endDate: string,
  configuration: HistoricalAnalysisConfiguration,
): string | null {
  const range = inclusiveDateRangeToApiRange(startDate, endDate);
  const days = inclusiveRangeDays(startDate, endDate);
  if (!range || days === null) {
    return "Choose a valid UTC start and end date.";
  }
  if (startDate > endDate) {
    return "The UTC start date must be on or before the end date.";
  }

  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);
  const todayValue = today.toISOString().slice(0, 10);
  if (endDate >= todayValue) {
    return "The UTC end date must be a completed day and cannot be in the future.";
  }
  if (days < configuration.minimumRangeDays) {
    return `Choose at least ${configuration.minimumRangeDays} complete UTC days.`;
  }
  if (days > configuration.maximumRangeDays) {
    return `Choose no more than ${configuration.maximumRangeDays} complete UTC days.`;
  }

  return null;
}

export function AnalysisForm({
  configuration,
  isSubmitting,
  markets,
  onSubmit,
  presets,
}: AnalysisFormProps) {
  const availableMarkets = useMemo(
    () =>
      markets.filter(
        (market) =>
          market.status === "available" &&
          market.baseAsset !== null &&
          market.quoteAsset !== null,
      ),
    [markets],
  );
  const availablePresets = useMemo(
    () => presets.filter((preset) => preset.status === "available"),
    [presets],
  );
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedPresetKey, setSelectedPresetKey] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const idempotencyKey = useRef<string | null>(null);
  const rangeInitialized = useRef(false);

  useEffect(() => {
    if (
      !availableMarkets.some((market) => market.symbol === selectedSymbol) &&
      availableMarkets[0]
    ) {
      setSelectedSymbol(availableMarkets[0].symbol);
    }
  }, [availableMarkets, selectedSymbol]);

  useEffect(() => {
    if (
      !availablePresets.some((preset) => presetKey(preset) === selectedPresetKey) &&
      availablePresets[0]
    ) {
      setSelectedPresetKey(presetKey(availablePresets[0]));
    }
  }, [availablePresets, selectedPresetKey]);

  useEffect(() => {
    if (rangeInitialized.current) {
      return;
    }

    const defaultRange = getDefaultUtcDateRange(
      configuration.minimumRangeDays,
      configuration.maximumRangeDays,
    );
    setStartDate(defaultRange.startDate);
    setEndDate(defaultRange.endDate);
    rangeInitialized.current = true;
  }, [configuration.maximumRangeDays, configuration.minimumRangeDays]);

  const selectedMarket = availableMarkets.find(
    (market) => market.symbol === selectedSymbol,
  );
  const selectedPreset = availablePresets.find(
    (preset) => presetKey(preset) === selectedPresetKey,
  );

  function handleBeginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    if (!selectedMarket || !selectedPreset) {
      setFormError("Choose a supported market and fixed preset version.");
      return;
    }

    const rangeError = validateDateRange(startDate, endDate, configuration);
    if (rangeError) {
      setFormError(rangeError);
      return;
    }

    setIsReviewOpen(true);
  }

  async function handleConfirmSubmit() {
    if (
      isSubmitting ||
      !selectedMarket ||
      !selectedPreset ||
      !inclusiveDateRangeToApiRange(startDate, endDate)
    ) {
      return;
    }

    const range = inclusiveDateRangeToApiRange(startDate, endDate);
    if (!range) {
      return;
    }

    const request: HistoricalAnalysisCreateRequest = {
      exchange: "binance",
      market_type: "spot",
      symbol: selectedMarket.symbol,
      preset_code: selectedPreset.code,
      preset_version: selectedPreset.version,
      analysis_start: range.analysisStart,
      analysis_end: range.analysisEnd,
    };
    const key = idempotencyKey.current ?? createIdempotencyKey();
    idempotencyKey.current = key;
    setFormError(null);

    try {
      await onSubmit(request, key);
      idempotencyKey.current = null;
      setIsReviewOpen(false);
    } catch (requestError) {
      if (requestError instanceof HistoricalAnalysisApiError) {
        idempotencyKey.current = null;
      }
      setFormError(historicalAnalysisErrorMessage(requestError));
    }
  }

  function handleReviewOpenChange(open: boolean) {
    if (!open && isSubmitting) {
      return;
    }
    setIsReviewOpen(open);
  }

  if (!availableMarkets.length || !availablePresets.length) {
    return (
      <Card>
        <CardContent className="space-y-4 p-6">
          <p>
            Historical analysis is unavailable until a supported market and
            fixed preset are available from the server.
          </p>
          <AssumptionsCard configuration={configuration} />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <AssumptionsCard configuration={configuration} />

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>
            Choose a supported market, fixed preset version, and completed UTC
            date range. The server owns the calculation and simulation meaning.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-6" onSubmit={handleBeginSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="historical-analysis-market">
                  Supported market
                </Label>
                <Select
                  disabled={isSubmitting || isReviewOpen}
                  onValueChange={(value) => {
                    setSelectedSymbol(value);
                    setFormError(null);
                  }}
                  value={selectedSymbol}
                >
                  <SelectTrigger
                    aria-label="Supported market"
                    className="w-full"
                    id="historical-analysis-market"
                  >
                    <SelectValue placeholder="Choose a market" />
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
                <Label htmlFor="historical-analysis-preset">
                  Fixed preset version
                </Label>
                <Select
                  disabled={isSubmitting || isReviewOpen}
                  onValueChange={(value) => {
                    setSelectedPresetKey(value);
                    setFormError(null);
                  }}
                  value={selectedPresetKey}
                >
                  <SelectTrigger
                    aria-label="Fixed preset version"
                    className="w-full"
                    id="historical-analysis-preset"
                  >
                    <SelectValue placeholder="Choose a preset" />
                  </SelectTrigger>
                  <SelectContent>
                    {availablePresets.map((preset) => (
                      <SelectItem key={presetKey(preset)} value={presetKey(preset)}>
                        {preset.name} · {formatTimeframe(preset.timeframe)} · v
                        {preset.version}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {selectedPreset ? (
              <Card className="bg-muted/30" size="sm">
                <CardHeader>
                  <CardTitle className="text-sm">Selected preset</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                    <div>
                      <dt className="font-medium">Direction</dt>
                      <dd className="text-muted-foreground">
                        {formatDirection(selectedPreset.direction)}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-medium">Strategy type</dt>
                      <dd className="text-muted-foreground">
                        {formatStrategyType(selectedPreset.strategyType)}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-medium">Timeframe</dt>
                      <dd className="text-muted-foreground">
                        {formatTimeframe(selectedPreset.timeframe)}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-medium">Fixed period</dt>
                      <dd className="text-muted-foreground">
                        {selectedPreset.parameters.period}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-medium">Threshold</dt>
                      <dd className="text-muted-foreground">
                        {selectedPreset.parameters.threshold ?? "None"}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-medium">Version</dt>
                      <dd className="text-muted-foreground">
                        v{selectedPreset.version}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="historical-analysis-start">Start date (UTC)</Label>
                <Input
                  disabled={isSubmitting || isReviewOpen}
                  id="historical-analysis-start"
                  max={endDate || undefined}
                  onChange={(event) => {
                    setStartDate(event.target.value);
                    setFormError(null);
                  }}
                  type="date"
                  value={startDate}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="historical-analysis-end">
                  End date (UTC, inclusive)
                </Label>
                <Input
                  disabled={isSubmitting || isReviewOpen}
                  id="historical-analysis-end"
                  min={startDate || undefined}
                  onChange={(event) => {
                    setEndDate(event.target.value);
                    setFormError(null);
                  }}
                  type="date"
                  value={endDate}
                />
              </div>
            </div>

            <p className="text-sm leading-6 text-muted-foreground">
              The server receives a start-inclusive, end-exclusive UTC range of{" "}
              {configuration.minimumRangeDays}–{configuration.maximumRangeDays} days.
              Boundaries are aligned for the selected preset timeframe.
            </p>

            {formError ? <InlineError message={formError} title="Review the analysis request" /> : null}

            <Button disabled={isSubmitting} type="submit">
              Review analysis
            </Button>
          </form>
        </CardContent>
      </Card>

      {selectedMarket && selectedPreset ? (
        <Dialog onOpenChange={handleReviewOpenChange} open={isReviewOpen}>
        <DialogContent
          className="max-h-[min(90svh,44rem)] max-w-2xl overflow-y-auto"
          onEscapeKeyDown={(event) => {
            if (isSubmitting) {
              event.preventDefault();
            }
          }}
          onPointerDownOutside={(event) => {
            if (isSubmitting) {
              event.preventDefault();
            }
          }}
          showCloseButton={!isSubmitting}
        >
          <DialogHeader>
            <DialogTitle>Review analysis</DialogTitle>
            <DialogDescription>
              Confirm the exact server-controlled request before it is queued.
            </DialogDescription>
          </DialogHeader>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium">Market</dt>
              <dd className="text-muted-foreground">{selectedMarket.symbol}</dd>
            </div>
            <div>
              <dt className="font-medium">Preset</dt>
              <dd className="text-muted-foreground">
                {selectedPreset.name} · v{selectedPreset.version}
              </dd>
            </div>
            <div>
              <dt className="font-medium">Timeframe</dt>
              <dd className="text-muted-foreground">
                {formatTimeframe(selectedPreset.timeframe)}
              </dd>
            </div>
            <div>
              <dt className="font-medium">UTC range</dt>
              <dd className="text-muted-foreground">
                {startDate} 00:00 through {endDate} 24:00 UTC
              </dd>
            </div>
            <div>
              <dt className="font-medium">Simulation version</dt>
              <dd className="text-muted-foreground">
                {configuration.simulationVersion}
              </dd>
            </div>
            <div>
              <dt className="font-medium">Assumption version</dt>
              <dd className="text-muted-foreground">
                {configuration.assumptionVersion}
              </dd>
            </div>
          </dl>
          <Alert>
            <AlertTitle>No live side effects</AlertTitle>
            <AlertDescription>
              Queueing this request does not create a live signal, alert,
              Telegram message, provider request, or trading action.
            </AlertDescription>
          </Alert>
          {formError ? (
            <InlineError message={formError} title="Analysis request failed" />
          ) : null}
          <DialogFooter>
            <Button
              disabled={isSubmitting}
              onClick={() => setIsReviewOpen(false)}
              type="button"
              variant="outline"
            >
              Back
            </Button>
            <Button
              aria-busy={isSubmitting}
              disabled={isSubmitting}
              onClick={() => void handleConfirmSubmit()}
              type="button"
            >
              {isSubmitting ? "Queueing analysis…" : "Confirm and queue analysis"}
            </Button>
          </DialogFooter>
        </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}
