"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

import { InlineError } from "@/components/inline-error";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { createIdempotencyKey } from "@/lib/idempotency";

import type { SupportedMarket } from "../markets/types";
import { AnalysisInfoDialog } from "./analysis-info-dialog";
import { HistoricalAnalysisApiError } from "./api";
import { historicalAnalysisErrorMessage } from "./errors";
import {
  formatBasisPoints,
  formatDirection,
  formatExitRuleType,
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
  HistoricalAnalysisExitRuleType,
  HistoricalAnalysisRun,
  HistoricalAnalysisStrategyExitRule,
  HistoricalAnalysisStrategyRequest,
  HistoricalAnalysisStrategyRuleCapability,
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

type StrategyDraft = {
  takeProfitEnabled: boolean;
  takeProfitPercent: string;
  stopLossEnabled: boolean;
  stopLossPercent: string;
  rsiExitEnabled: boolean;
  rsiExitDirection: string;
  rsiExitThreshold: string;
  maxHoldingCandles: string;
};

type StrategyField =
  | "positionDirection"
  | "takeProfitPercent"
  | "stopLossPercent"
  | "rsiExitDirection"
  | "rsiExitThreshold"
  | "maxHoldingCandles";

type StrategyFieldErrors = Partial<Record<StrategyField, string>>;

const OPTIONAL_RULE_TYPES: HistoricalAnalysisExitRuleType[] = [
  "take_profit_percent",
  "stop_loss_percent",
  "rsi_threshold_cross",
];

function presetKey(preset: AvailableHistoricalPreset): string {
  return `${preset.code}:${preset.version}`;
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

function defaultCapabilityValue(
  capability: HistoricalAnalysisStrategyRuleCapability | undefined,
  fallback: string,
): string {
  return capability?.default === undefined
    ? fallback
    : String(capability.default);
}

function initialStrategyDraft(
  configuration: HistoricalAnalysisConfiguration,
): StrategyDraft {
  const capabilities = configuration.strategyCapabilities;
  const takeProfit = capabilities?.exitRuleLimits?.take_profit_percent;
  const stopLoss = capabilities?.exitRuleLimits?.stop_loss_percent;
  const rsiExit = capabilities?.exitRuleLimits?.rsi_threshold_cross;

  return {
    takeProfitEnabled: false,
    takeProfitPercent: defaultCapabilityValue(takeProfit, "6"),
    stopLossEnabled: false,
    stopLossPercent: defaultCapabilityValue(stopLoss, "3"),
    rsiExitEnabled: false,
    rsiExitDirection: rsiExit?.directions?.[0] ?? "cross_below",
    rsiExitThreshold: defaultCapabilityValue(rsiExit, "20"),
    maxHoldingCandles: String(capabilities?.maxHoldingCandles.default ?? 6),
  };
}

function isRuleSupported(
  configuration: HistoricalAnalysisConfiguration,
  type: HistoricalAnalysisExitRuleType,
): boolean {
  const capabilities = configuration.strategyCapabilities;
  if (!capabilities) {
    return false;
  }
  if (capabilities.supportedExitRuleTypes) {
    return capabilities.supportedExitRuleTypes.includes(type);
  }
  return Boolean(capabilities.exitRuleLimits?.[type]);
}

function ruleCapability(
  configuration: HistoricalAnalysisConfiguration,
  type: HistoricalAnalysisExitRuleType,
): HistoricalAnalysisStrategyRuleCapability | undefined {
  return configuration.strategyCapabilities?.exitRuleLimits?.[type];
}

function validDecimal(value: string): boolean {
  return /^\d+(?:\.\d+)?$/.test(value.trim());
}

function numericValue(value: string | number | undefined): number | null {
  if (value === undefined) {
    return null;
  }
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function validateDecimalField(
  value: string,
  capability: HistoricalAnalysisStrategyRuleCapability | undefined,
  label: string,
  field: StrategyField,
  errors: StrategyFieldErrors,
): void {
  if (!value.trim()) {
    errors[field] = `${label} is required.`;
    return;
  }
  if (!validDecimal(value)) {
    errors[field] = `${label} must be a positive decimal.`;
    return;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    errors[field] = `${label} must be greater than zero.`;
    return;
  }

  const minimum = numericValue(capability?.minimum);
  const maximum = numericValue(capability?.maximum);
  const minimumExclusive = numericValue(capability?.minimumExclusive);
  const maximumExclusive = numericValue(capability?.maximumExclusive);
  if (
    minimum !== null &&
    (capability?.minimumExclusive === true
      ? parsed <= minimum
      : capability?.minimumInclusive === false
        ? parsed <= minimum
        : parsed < minimum)
  ) {
    errors[field] = `${label} is below the server-supported minimum.`;
  } else if (
    maximum !== null &&
    (capability?.maximumExclusive === true
      ? parsed >= maximum
      : capability?.maximumInclusive === false
        ? parsed >= maximum
        : parsed > maximum)
  ) {
    errors[field] = `${label} is above the server-supported maximum.`;
  } else if (minimumExclusive !== null && parsed <= minimumExclusive) {
    errors[field] = `${label} must be above the server-supported minimum.`;
  } else if (maximumExclusive !== null && parsed >= maximumExclusive) {
    errors[field] = `${label} must be below the server-supported maximum.`;
  }
}

function validateStrategy(
  configuration: HistoricalAnalysisConfiguration,
  draft: StrategyDraft,
): { formError: string | null; fieldErrors: StrategyFieldErrors } {
  const capabilities = configuration.strategyCapabilities;
  if (!capabilities?.configurableStrategyAvailable) {
    return { formError: null, fieldErrors: {} };
  }

  const fieldErrors: StrategyFieldErrors = {};
  if (!capabilities.positionDirections.includes("long")) {
    fieldErrors.positionDirection = "Long strategies are not currently available.";
  }

  const enabledOptionalRuleCount = [
    draft.takeProfitEnabled,
    draft.stopLossEnabled,
    draft.rsiExitEnabled,
  ].filter(Boolean).length;
  if (enabledOptionalRuleCount + 1 > capabilities.maximumExitRules) {
    return {
      formError: `Choose no more than ${capabilities.maximumExitRules} exit rules.`,
      fieldErrors,
    };
  }

  const requiredTypes = new Set(capabilities.requiredExitRuleTypes);
  if (requiredTypes.has("max_holding_candles")) {
    const parsed = Number(draft.maxHoldingCandles);
    if (!/^\d+$/.test(draft.maxHoldingCandles) || !Number.isInteger(parsed)) {
      fieldErrors.maxHoldingCandles = "Maximum holding must be a whole number of candles.";
    } else if (
      parsed < capabilities.maxHoldingCandles.minimum ||
      parsed > capabilities.maxHoldingCandles.maximum
    ) {
      fieldErrors.maxHoldingCandles = "Maximum holding is outside the server-supported range.";
    }
  }

  if (draft.takeProfitEnabled) {
    validateDecimalField(
      draft.takeProfitPercent,
      ruleCapability(configuration, "take_profit_percent"),
      "Take-profit percentage",
      "takeProfitPercent",
      fieldErrors,
    );
  }
  if (draft.stopLossEnabled) {
    validateDecimalField(
      draft.stopLossPercent,
      ruleCapability(configuration, "stop_loss_percent"),
      "Stop-loss percentage",
      "stopLossPercent",
      fieldErrors,
    );
  }
  if (draft.rsiExitEnabled) {
    const rsiCapability = ruleCapability(configuration, "rsi_threshold_cross");
    if (
      !rsiCapability?.directions?.includes(draft.rsiExitDirection) &&
      rsiCapability?.directions
    ) {
      fieldErrors.rsiExitDirection = "Choose a server-supported RSI direction.";
    }
    validateDecimalField(
      draft.rsiExitThreshold,
      rsiCapability,
      "RSI threshold",
      "rsiExitThreshold",
      fieldErrors,
    );
  }

  const missingRequiredRule = [...requiredTypes].find((type) => {
    if (type === "max_holding_candles") {
      return false;
    }
    if (type === "take_profit_percent") {
      return !draft.takeProfitEnabled;
    }
    if (type === "stop_loss_percent") {
      return !draft.stopLossEnabled;
    }
    return !draft.rsiExitEnabled;
  });
  if (missingRequiredRule) {
    return {
      formError: `${formatExitRuleType(missingRequiredRule)} is required by the server.`,
      fieldErrors,
    };
  }

  return {
    formError: Object.keys(fieldErrors).length ? "Review the highlighted strategy fields." : null,
    fieldErrors,
  };
}

function strategyRequest(
  configuration: HistoricalAnalysisConfiguration,
  draft: StrategyDraft,
): HistoricalAnalysisStrategyRequest | undefined {
  if (!configuration.strategyCapabilities?.configurableStrategyAvailable) {
    return undefined;
  }

  const exitRules: HistoricalAnalysisStrategyExitRule[] = [];
  if (draft.takeProfitEnabled) {
    exitRules.push({ type: "take_profit_percent", percent: draft.takeProfitPercent });
  }
  if (draft.stopLossEnabled) {
    exitRules.push({ type: "stop_loss_percent", percent: draft.stopLossPercent });
  }
  if (draft.rsiExitEnabled) {
    exitRules.push({
      type: "rsi_threshold_cross",
      direction: draft.rsiExitDirection,
      threshold: draft.rsiExitThreshold,
    });
  }
  exitRules.push({
    type: "max_holding_candles",
    candles: Number(draft.maxHoldingCandles),
  });

  return {
    position_direction: "long",
    exit_rules: exitRules,
  };
}

function strategyFieldFromDetail(
  field: string,
  submittedRuleTypes: HistoricalAnalysisExitRuleType[],
): StrategyField | null {
  if (field === "strategy.positionDirection") {
    return "positionDirection";
  }

  const ruleMatch = field.match(/strategy\.exitRules\[(\d+)\](?:\.(\w+))?/);
  if (!ruleMatch) {
    return null;
  }

  const type = submittedRuleTypes[Number(ruleMatch[1])];
  if (type === "take_profit_percent") {
    return "takeProfitPercent";
  }
  if (type === "stop_loss_percent") {
    return "stopLossPercent";
  }
  if (type === "rsi_threshold_cross") {
    return ruleMatch[2] === "direction" ? "rsiExitDirection" : "rsiExitThreshold";
  }
  if (type === "max_holding_candles") {
    return "maxHoldingCandles";
  }
  return null;
}

function strategyDetailMessage(code: string): string {
  switch (code) {
    case "REQUIRED":
      return "This value is required.";
    case "OUT_OF_RANGE":
    case "MINIMUM":
    case "MAXIMUM":
      return "This value is outside the server-supported range.";
    case "UNSUPPORTED":
      return "This option is not supported for the selected strategy.";
    case "DUPLICATE":
    case "CONFLICTING_RULES":
      return "This exit rule conflicts with another selected rule.";
    default:
      return "Review this strategy field.";
  }
}

function strategyFieldErrorsFromApi(
  details: HistoricalAnalysisApiError["details"],
  submittedRuleTypes: HistoricalAnalysisExitRuleType[],
): StrategyFieldErrors {
  return details.reduce<StrategyFieldErrors>((errors, detail) => {
    const field = strategyFieldFromDetail(detail.field, submittedRuleTypes);
    if (field) {
      errors[field] = strategyDetailMessage(detail.code);
    }
    return errors;
  }, {});
}

function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? (
    <p className="text-sm text-destructive" id={id} role="alert">
      {message}
    </p>
  ) : null;
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
  const [strategyDraft, setStrategyDraft] = useState<StrategyDraft>(() =>
    initialStrategyDraft(configuration),
  );
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<StrategyFieldErrors>({});
  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const idempotencyKey = useRef<string | null>(null);
  const rangeInitialized = useRef(false);
  const strategyInitialized = useRef(false);
  const submittedRuleTypes = useRef<HistoricalAnalysisExitRuleType[]>([]);

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

  useEffect(() => {
    if (strategyInitialized.current) {
      return;
    }
    setStrategyDraft(initialStrategyDraft(configuration));
    strategyInitialized.current = true;
  }, [configuration]);

  const selectedMarket = availableMarkets.find(
    (market) => market.symbol === selectedSymbol,
  );
  const selectedPreset = availablePresets.find(
    (preset) => presetKey(preset) === selectedPresetKey,
  );
  const strategyCapabilities = configuration.strategyCapabilities;
  const configurableStrategyAvailable =
    strategyCapabilities?.configurableStrategyAvailable === true;
  const strategyRulesAvailable = configurableStrategyAvailable;
  const supportsTakeProfit = isRuleSupported(configuration, "take_profit_percent");
  const supportsStopLoss = isRuleSupported(configuration, "stop_loss_percent");
  const supportsRsiExit = isRuleSupported(configuration, "rsi_threshold_cross");
  const rsiDirections =
    ruleCapability(configuration, "rsi_threshold_cross")?.directions ?? [];

  function clearRequestIdentity(): void {
    idempotencyKey.current = null;
    setFormError(null);
    setFieldErrors({});
  }

  function updateStrategyDraft(update: Partial<StrategyDraft>): void {
    clearRequestIdentity();
    setStrategyDraft((current) => ({ ...current, ...update }));
  }

  function handleBeginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});

    if (!selectedMarket || !selectedPreset) {
      setFormError("Choose a market and signal.");
      return;
    }

    const rangeError = validateDateRange(startDate, endDate, configuration);
    if (rangeError) {
      setFormError(rangeError);
      return;
    }

    const strategyValidation = validateStrategy(configuration, strategyDraft);
    if (strategyValidation.formError || Object.keys(strategyValidation.fieldErrors).length) {
      setFormError(strategyValidation.formError);
      setFieldErrors(strategyValidation.fieldErrors);
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

    const strategy = strategyRequest(configuration, strategyDraft);
    submittedRuleTypes.current = strategy?.exit_rules.map((rule) => rule.type) ?? [];
    const request: HistoricalAnalysisCreateRequest = {
      exchange: "binance",
      market_type: "spot",
      symbol: selectedMarket.symbol,
      preset_code: selectedPreset.code,
      preset_version: selectedPreset.version,
      analysis_start: range.analysisStart,
      analysis_end: range.analysisEnd,
      ...(strategy ? { strategy } : {}),
    };
    const key = idempotencyKey.current ?? createIdempotencyKey();
    idempotencyKey.current = key;
    setFormError(null);
    setFieldErrors({});

    try {
      await onSubmit(request, key);
      idempotencyKey.current = null;
      setIsReviewOpen(false);
    } catch (requestError) {
      if (requestError instanceof HistoricalAnalysisApiError) {
        idempotencyKey.current = null;
        setFieldErrors(
          strategyFieldErrorsFromApi(
            requestError.details,
            submittedRuleTypes.current,
          ),
        );
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

  function fieldDescribedBy(field: StrategyField, helpId: string): string {
    return fieldErrors[field] ? `${helpId} ${helpId}-error` : helpId;
  }

  if (!availableMarkets.length || !availablePresets.length) {
    return (
      <Card>
        <CardContent className="space-y-4 p-6">
          <p>
            Historical analysis is unavailable until a supported market and
            signal are available.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1.5">
              <CardTitle>Start an analysis</CardTitle>
              <CardDescription>
                Configure the entry, exits, and completed UTC date range.
              </CardDescription>
            </div>
            <AnalysisInfoDialog configuration={configuration} />
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-8" onSubmit={handleBeginSubmit}>
            <section aria-labelledby="historical-analysis-entry-heading" className="space-y-4">
              <div>
                <h3 className="font-semibold" id="historical-analysis-entry-heading">
                  1. Entry
                </h3>
                <p className="text-sm text-muted-foreground">
                  Select a server-controlled market and fixed entry signal.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="historical-analysis-market">Market</Label>
                  <Select
                    disabled={isSubmitting || isReviewOpen}
                    onValueChange={(value) => {
                      clearRequestIdentity();
                      setSelectedSymbol(value);
                    }}
                    value={selectedSymbol}
                  >
                    <SelectTrigger
                      aria-label="Market"
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
                  <Label htmlFor="historical-analysis-preset">Signal</Label>
                  <Select
                    disabled={isSubmitting || isReviewOpen}
                    onValueChange={(value) => {
                      clearRequestIdentity();
                      setSelectedPresetKey(value);
                    }}
                    value={selectedPresetKey}
                  >
                    <SelectTrigger
                      aria-label="Signal"
                      className="w-full"
                      id="historical-analysis-preset"
                    >
                      <SelectValue placeholder="Choose a signal" />
                    </SelectTrigger>
                    <SelectContent>
                      {availablePresets.map((preset) => (
                        <SelectItem key={presetKey(preset)} value={presetKey(preset)}>
                          {preset.name} ({formatTimeframe(preset.timeframe)}) - v
                          {preset.version}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {selectedPreset ? (
                <Card className="bg-muted/30" size="sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Selected entry</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <p className="font-medium">
                      {selectedPreset.name} ({formatTimeframe(selectedPreset.timeframe)})
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatDirection(selectedPreset.direction)} -{" "}
                      {formatStrategyType(selectedPreset.strategyType)} - period{" "}
                      {selectedPreset.parameters.period} - threshold{" "}
                      {selectedPreset.parameters.threshold ?? "none"} - v
                      {selectedPreset.version}
                    </p>
                    {strategyRulesAvailable ? (
                      <p className="pt-2 font-medium text-primary">
                        This signal opens LONG at the next candle open.
                      </p>
                    ) : null}
                  </CardContent>
                </Card>
              ) : null}
            </section>

            {strategyRulesAvailable ? (
              <section aria-labelledby="historical-analysis-exit-heading" className="space-y-4">
                <div>
                  <h3 className="font-semibold" id="historical-analysis-exit-heading">
                    2. Exit plan
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Add supported exits. Maximum holding is required for every configurable run.
                  </p>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  {supportsTakeProfit ? (
                    <Card size="sm">
                      <CardContent className="space-y-3 p-4">
                        <div className="flex items-center justify-between gap-4">
                          <Label className="font-medium" htmlFor="historical-analysis-take-profit-enabled">
                            Take profit
                          </Label>
                          <Switch
                            aria-label="Enable take profit"
                            checked={strategyDraft.takeProfitEnabled}
                            disabled={isSubmitting || isReviewOpen}
                            id="historical-analysis-take-profit-enabled"
                            onCheckedChange={(checked) => updateStrategyDraft({ takeProfitEnabled: checked })}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="historical-analysis-take-profit-percent">
                            Close when price increases by (%)
                          </Label>
                          <Input
                            aria-describedby={fieldDescribedBy("takeProfitPercent", "historical-analysis-take-profit-help")}
                            aria-invalid={Boolean(fieldErrors.takeProfitPercent)}
                            disabled={isSubmitting || isReviewOpen || !strategyDraft.takeProfitEnabled}
                            id="historical-analysis-take-profit-percent"
                            inputMode="decimal"
                            onChange={(event) => updateStrategyDraft({ takeProfitPercent: event.target.value })}
                            type="text"
                            value={strategyDraft.takeProfitPercent}
                          />
                          <p className="text-xs text-muted-foreground" id="historical-analysis-take-profit-help">
                            The server validates the exact decimal value.
                          </p>
                          <FieldError id="historical-analysis-take-profit-help-error" message={fieldErrors.takeProfitPercent} />
                        </div>
                      </CardContent>
                    </Card>
                  ) : null}

                  {supportsStopLoss ? (
                    <Card size="sm">
                      <CardContent className="space-y-3 p-4">
                        <div className="flex items-center justify-between gap-4">
                          <Label className="font-medium" htmlFor="historical-analysis-stop-loss-enabled">
                            Stop loss
                          </Label>
                          <Switch
                            aria-label="Enable stop loss"
                            checked={strategyDraft.stopLossEnabled}
                            disabled={isSubmitting || isReviewOpen}
                            id="historical-analysis-stop-loss-enabled"
                            onCheckedChange={(checked) => updateStrategyDraft({ stopLossEnabled: checked })}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="historical-analysis-stop-loss-percent">
                            Close when price decreases by (%)
                          </Label>
                          <Input
                            aria-describedby={fieldDescribedBy("stopLossPercent", "historical-analysis-stop-loss-help")}
                            aria-invalid={Boolean(fieldErrors.stopLossPercent)}
                            disabled={isSubmitting || isReviewOpen || !strategyDraft.stopLossEnabled}
                            id="historical-analysis-stop-loss-percent"
                            inputMode="decimal"
                            onChange={(event) => updateStrategyDraft({ stopLossPercent: event.target.value })}
                            type="text"
                            value={strategyDraft.stopLossPercent}
                          />
                          <p className="text-xs text-muted-foreground" id="historical-analysis-stop-loss-help">
                            The server validates the exact decimal value.
                          </p>
                          <FieldError id="historical-analysis-stop-loss-help-error" message={fieldErrors.stopLossPercent} />
                        </div>
                      </CardContent>
                    </Card>
                  ) : null}

                  {supportsRsiExit ? (
                    <Card size="sm">
                      <CardContent className="space-y-3 p-4">
                        <div className="flex items-center justify-between gap-4">
                          <Label className="font-medium" htmlFor="historical-analysis-rsi-exit-enabled">
                            Indicator exit
                          </Label>
                          <Switch
                            aria-label="Enable indicator exit"
                            checked={strategyDraft.rsiExitEnabled}
                            disabled={isSubmitting || isReviewOpen}
                            id="historical-analysis-rsi-exit-enabled"
                            onCheckedChange={(checked) => updateStrategyDraft({ rsiExitEnabled: checked })}
                          />
                        </div>
                        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                          <div className="space-y-2">
                            <Label htmlFor="historical-analysis-rsi-exit-direction">RSI(14) condition</Label>
                            <Select
                              disabled={isSubmitting || isReviewOpen || !strategyDraft.rsiExitEnabled}
                              onValueChange={(value) => updateStrategyDraft({ rsiExitDirection: value })}
                              value={strategyDraft.rsiExitDirection}
                            >
                              <SelectTrigger
                                aria-describedby={fieldDescribedBy("rsiExitDirection", "historical-analysis-rsi-exit-help")}
                                aria-invalid={Boolean(fieldErrors.rsiExitDirection)}
                                className="w-full"
                                id="historical-analysis-rsi-exit-direction"
                              >
                                <SelectValue placeholder="Choose condition" />
                              </SelectTrigger>
                              <SelectContent>
                                {rsiDirections.map((direction) => (
                                  <SelectItem key={direction} value={direction}>
                                    {direction === "cross_below" ? "crosses below" : "crosses above"}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="historical-analysis-rsi-exit-threshold">Threshold</Label>
                            <Input
                              aria-describedby={fieldDescribedBy("rsiExitThreshold", "historical-analysis-rsi-exit-help")}
                              aria-invalid={Boolean(fieldErrors.rsiExitThreshold)}
                              disabled={isSubmitting || isReviewOpen || !strategyDraft.rsiExitEnabled}
                              id="historical-analysis-rsi-exit-threshold"
                              inputMode="decimal"
                              onChange={(event) => updateStrategyDraft({ rsiExitThreshold: event.target.value })}
                              type="text"
                              value={strategyDraft.rsiExitThreshold}
                            />
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground" id="historical-analysis-rsi-exit-help">
                          The server pins RSI(14), close input, the entry timeframe, and its calculation version.
                        </p>
                        <FieldError id="historical-analysis-rsi-exit-help-error" message={fieldErrors.rsiExitDirection ?? fieldErrors.rsiExitThreshold} />
                      </CardContent>
                    </Card>
                  ) : null}

                  <Card size="sm">
                    <CardContent className="space-y-3 p-4">
                      <div>
                        <Label htmlFor="historical-analysis-max-holding">Maximum holding</Label>
                        <p className="text-xs text-muted-foreground">Required for a deterministic terminal exit.</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Input
                          aria-describedby={fieldDescribedBy("maxHoldingCandles", "historical-analysis-max-holding-help")}
                          aria-invalid={Boolean(fieldErrors.maxHoldingCandles)}
                          disabled={isSubmitting || isReviewOpen}
                          id="historical-analysis-max-holding"
                          inputMode="numeric"
                          min={strategyCapabilities?.maxHoldingCandles.minimum}
                          max={strategyCapabilities?.maxHoldingCandles.maximum}
                          onChange={(event) => updateStrategyDraft({ maxHoldingCandles: event.target.value })}
                          type="number"
                          value={strategyDraft.maxHoldingCandles}
                        />
                        <span className="shrink-0 text-sm text-muted-foreground">candles</span>
                      </div>
                      <p className="text-xs text-muted-foreground" id="historical-analysis-max-holding-help">
                        Server range: {strategyCapabilities?.maxHoldingCandles.minimum}–{strategyCapabilities?.maxHoldingCandles.maximum} candles.
                      </p>
                      <FieldError id="historical-analysis-max-holding-help-error" message={fieldErrors.maxHoldingCandles} />
                    </CardContent>
                  </Card>
                </div>

                <Alert>
                  <AlertTitle>Same-candle priority</AlertTitle>
                  <AlertDescription>
                    {strategyCapabilities?.sameCandlePriority.map(formatExitRuleType).join(" → ")}
                    . The server determines the simulation result.
                  </AlertDescription>
                </Alert>
              </section>
            ) : null}

            <section aria-labelledby="historical-analysis-period-heading" className="space-y-4">
              <div>
                <h3 className="font-semibold" id="historical-analysis-period-heading">
                  {strategyRulesAvailable ? "3" : "2"}. Period
                </h3>
                <p className="text-sm text-muted-foreground">Choose completed UTC days only.</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="historical-analysis-start">Start date (UTC)</Label>
                  <Input
                    disabled={isSubmitting || isReviewOpen}
                    id="historical-analysis-start"
                    max={endDate || undefined}
                    onChange={(event) => {
                      clearRequestIdentity();
                      setStartDate(event.target.value);
                    }}
                    type="date"
                    value={startDate}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="historical-analysis-end">End date (UTC)</Label>
                  <Input
                    disabled={isSubmitting || isReviewOpen}
                    id="historical-analysis-end"
                    min={startDate || undefined}
                    onChange={(event) => {
                      clearRequestIdentity();
                      setEndDate(event.target.value);
                    }}
                    type="date"
                    value={endDate}
                  />
                </div>
              </div>
              <p className="text-sm text-muted-foreground">
                Choose {configuration.minimumRangeDays}-{configuration.maximumRangeDays} completed UTC days.
              </p>
            </section>

            {strategyRulesAvailable ? (
              <section aria-labelledby="historical-analysis-assumptions-heading" className="space-y-3">
                <h3 className="font-semibold" id="historical-analysis-assumptions-heading">
                  4. Execution assumptions
                </h3>
                <p className="text-sm text-muted-foreground">
                  Entry timing, fees, slippage, sizing, and overlap behavior are server-controlled.
                </p>
              </section>
            ) : null}

            {formError ? (
              <InlineError message={formError} title="Check your choices" />
            ) : null}

            <Button disabled={isSubmitting} type="submit">
              Review and run
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
                Check the exact strategy intent, then start the hypothetical simulation.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-5">
              <dl className="grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium">Market</dt>
                  <dd className="text-muted-foreground">{selectedMarket.symbol}</dd>
                </div>
                <div>
                  <dt className="font-medium">Entry</dt>
                  <dd className="text-muted-foreground">
                    {selectedPreset.name} (v{selectedPreset.version})
                  </dd>
                </div>
                <div>
                  <dt className="font-medium">Timeframe</dt>
                  <dd className="text-muted-foreground">{formatTimeframe(selectedPreset.timeframe)}</dd>
                </div>
                <div>
                  <dt className="font-medium">Date range</dt>
                  <dd className="text-muted-foreground">{startDate} to {endDate} (UTC)</dd>
                </div>
              </dl>

              {strategyRulesAvailable ? (
                <Card size="sm">
                  <CardHeader>
                    <CardTitle className="text-base">Strategy</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <dl className="grid gap-3 text-sm sm:grid-cols-2">
                      <div>
                        <dt className="font-medium">Position</dt>
                        <dd className="text-muted-foreground">LONG</dd>
                      </div>
                      <div>
                        <dt className="font-medium">Entry timing</dt>
                        <dd className="text-muted-foreground">Next candle open</dd>
                      </div>
                      {strategyDraft.takeProfitEnabled ? (
                        <div>
                          <dt className="font-medium">Take profit</dt>
                          <dd className="text-muted-foreground">+{strategyDraft.takeProfitPercent}%</dd>
                        </div>
                      ) : null}
                      {strategyDraft.stopLossEnabled ? (
                        <div>
                          <dt className="font-medium">Stop loss</dt>
                          <dd className="text-muted-foreground">-{strategyDraft.stopLossPercent}%</dd>
                        </div>
                      ) : null}
                      {strategyDraft.rsiExitEnabled ? (
                        <div>
                          <dt className="font-medium">Indicator exit</dt>
                          <dd className="text-muted-foreground">
                            RSI(14) {strategyDraft.rsiExitDirection === "cross_below" ? "crosses below" : "crosses above"}{" "}
                            {strategyDraft.rsiExitThreshold}
                          </dd>
                        </div>
                      ) : null}
                      <div>
                        <dt className="font-medium">Maximum holding</dt>
                        <dd className="text-muted-foreground">{strategyDraft.maxHoldingCandles} candles</dd>
                      </div>
                      <div>
                        <dt className="font-medium">Fee</dt>
                        <dd className="text-muted-foreground">{formatBasisPoints(configuration.assumptions.feeBpsPerSide)} per side</dd>
                      </div>
                      <div>
                        <dt className="font-medium">Slippage</dt>
                        <dd className="text-muted-foreground">{formatBasisPoints(configuration.assumptions.slippageBpsPerSide)} per side</dd>
                      </div>
                    </dl>
                  </CardContent>
                </Card>
              ) : null}

              <Alert>
                <AlertTitle>No live actions</AlertTitle>
                <AlertDescription>
                  This uses stored data only. It will not create alerts, send Telegram messages, or trade.
                </AlertDescription>
              </Alert>
              {formError ? (
                <InlineError message={formError} title="Could not start analysis" />
              ) : null}
            </div>
            <DialogFooter>
              <Button disabled={isSubmitting} onClick={() => setIsReviewOpen(false)} type="button" variant="outline">
                Back
              </Button>
              <Button
                aria-busy={isSubmitting}
                disabled={isSubmitting}
                onClick={() => void handleConfirmSubmit()}
                type="button"
              >
                {isSubmitting ? "Starting analysis..." : "Start analysis"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}
