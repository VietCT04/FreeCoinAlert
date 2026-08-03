"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { SupportedMarket } from "../markets/types";
import { HistoricalAnalysisApiError } from "./api";
import { historicalAnalysisErrorMessage } from "./errors";
import {
  formatBasisPoints,
  formatDirection,
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

function AssumptionDisclosure({
  configuration,
}: {
  configuration: HistoricalAnalysisConfiguration;
}) {
  const assumptions = configuration.assumptions;

  return (
    <aside className="space-y-3 rounded-lg bg-zinc-50 p-4 text-sm dark:bg-zinc-950">
      <h3 className="font-semibold">Server-controlled simulation assumptions</h3>
      <ul className="list-disc space-y-1 pl-5">
        <li>Signal: confirmed candle close</li>
        <li>Entry: next candle open</li>
        <li>Exit: close after {assumptions.holdingPeriodCandles} held candles</li>
        <li>Position: long for cross-above, synthetic short for cross-below</li>
        <li>Size: full hypothetical equity, one position at a time</li>
        <li>Fees: {formatBasisPoints(assumptions.feeBpsPerSide)} per side</li>
        <li>
          Slippage: {formatBasisPoints(assumptions.slippageBpsPerSide)} per side
        </li>
        <li>Overlapping signals: ignored</li>
        <li>Incomplete final trades: not opened</li>
      </ul>
      <p className="leading-6 text-zinc-600 dark:text-zinc-300">
        Synthetic short results are analytical inverse exposure. They are not
        executable Binance Spot trades and do not model borrowing, margin,
        leverage, liquidation, or derivatives.
      </p>
      <p className="leading-6 text-zinc-600 dark:text-zinc-300">
        This is a historical hypothetical simulation using stored candle data
        and fixed assumptions. It is not financial advice, a prediction, or a
        guarantee of future results. Real execution, liquidity, fees, slippage,
        and market behavior may differ.
      </p>
    </aside>
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
  const [isConfirming, setIsConfirming] = useState(false);
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

  function handleBeginSubmit(event: React.FormEvent<HTMLFormElement>) {
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

    setIsConfirming(true);
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
    const key = idempotencyKey.current ?? globalThis.crypto.randomUUID();
    idempotencyKey.current = key;
    setFormError(null);

    try {
      await onSubmit(request, key);
      idempotencyKey.current = null;
      setIsConfirming(false);
    } catch (requestError) {
      if (requestError instanceof HistoricalAnalysisApiError) {
        idempotencyKey.current = null;
      }
      setFormError(historicalAnalysisErrorMessage(requestError));
    }
  }

  if (!availableMarkets.length || !availablePresets.length) {
    return (
      <div className="space-y-3 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700">
        <p>
          Historical analysis is unavailable until a supported market and fixed
          preset are available from the server.
        </p>
        <AssumptionDisclosure configuration={configuration} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <AssumptionDisclosure configuration={configuration} />
      <form className="space-y-4" onSubmit={handleBeginSubmit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="font-medium" htmlFor="historical-analysis-market">
              Supported market
            </label>
            <select
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
              disabled={isSubmitting || isConfirming}
              id="historical-analysis-market"
              onChange={(event) => setSelectedSymbol(event.target.value)}
              value={selectedSymbol}
            >
              {availableMarkets.map((market) => (
                <option key={market.symbol} value={market.symbol}>
                  {market.baseAsset}/{market.quoteAsset} ({market.symbol})
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label className="font-medium" htmlFor="historical-analysis-preset">
              Fixed preset version
            </label>
            <select
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
              disabled={isSubmitting || isConfirming}
              id="historical-analysis-preset"
              onChange={(event) => setSelectedPresetKey(event.target.value)}
              value={selectedPresetKey}
            >
              {availablePresets.map((preset) => (
                <option key={presetKey(preset)} value={presetKey(preset)}>
                  {preset.name} · {formatTimeframe(preset.timeframe)} · v{preset.version}
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedPreset ? (
          <p className="text-sm text-zinc-600 dark:text-zinc-300">
            {formatDirection(selectedPreset.direction)} · {selectedPreset.strategyType} ·
            server period {selectedPreset.parameters.period}
            {selectedPreset.parameters.threshold
              ? ` · threshold ${selectedPreset.parameters.threshold}`
              : ""}
          </p>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="font-medium" htmlFor="historical-analysis-start">
              Start date (UTC)
            </label>
            <input
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
              disabled={isSubmitting || isConfirming}
              id="historical-analysis-start"
              onChange={(event) => setStartDate(event.target.value)}
              type="date"
              value={startDate}
            />
          </div>
          <div className="space-y-2">
            <label className="font-medium" htmlFor="historical-analysis-end">
              End date (UTC, inclusive)
            </label>
            <input
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950"
              disabled={isSubmitting || isConfirming}
              id="historical-analysis-end"
              onChange={(event) => setEndDate(event.target.value)}
              type="date"
              value={endDate}
            />
          </div>
        </div>

        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          The server receives a start-inclusive, end-exclusive UTC range of
          {" "}
          {configuration.minimumRangeDays}–{configuration.maximumRangeDays} days.
          Date boundaries are aligned for both 1h and 4h presets.
        </p>

        {!isConfirming ? (
          <button
            className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
            disabled={isSubmitting}
            type="submit"
          >
            Review analysis
          </button>
        ) : (
          <div className="space-y-4 rounded-lg border border-zinc-300 p-4 dark:border-zinc-700">
            <h3 className="font-semibold">Confirm historical analysis</h3>
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="font-medium">Market</dt>
                <dd>{selectedMarket.symbol}</dd>
              </div>
              <div>
                <dt className="font-medium">Preset</dt>
                <dd>
                  {selectedPreset.name} · v{selectedPreset.version} · {formatTimeframe(selectedPreset.timeframe)}
                </dd>
              </div>
              <div>
                <dt className="font-medium">UTC range</dt>
                <dd>
                  {startDate} 00:00 through {endDate} 24:00 UTC
                </dd>
              </div>
              <div>
                <dt className="font-medium">Versions</dt>
                <dd>
                  {configuration.simulationVersion} · {configuration.assumptionVersion}
                </dd>
              </div>
            </dl>
            <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              Submit one bounded server-controlled hypothetical simulation. No
              live signal, alert, Telegram message, or provider request is
              created by this analysis.
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                className="rounded-lg border border-zinc-300 px-4 py-2 font-medium disabled:opacity-60 dark:border-zinc-700"
                disabled={isSubmitting}
                onClick={() => setIsConfirming(false)}
                type="button"
              >
                Back
              </button>
              <button
                aria-busy={isSubmitting}
                className="rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
                disabled={isSubmitting}
                onClick={() => void handleConfirmSubmit()}
                type="button"
              >
                {isSubmitting ? "Queueing analysis…" : "Confirm and queue analysis"}
              </button>
            </div>
          </div>
        )}
      </form>
      {formError ? (
        <p aria-live="assertive" className="text-sm text-red-700 dark:text-red-300">
          {formError}
        </p>
      ) : null}
    </div>
  );
}
