"use client";

import { InfoIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { formatBasisPoints } from "./format";
import type { HistoricalAnalysisConfiguration } from "./types";

export function AnalysisInfoDialog({
  configuration,
}: {
  configuration: HistoricalAnalysisConfiguration;
}) {
  const { assumptions } = configuration;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          aria-label="More information about historical analysis"
          title="More information"
          type="button"
          variant="outline"
        >
          <InfoIcon aria-hidden="true" />
          Info
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[min(90svh,44rem)] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>About this analysis</DialogTitle>
          <DialogDescription>
            This tests a fixed signal against stored market data. Choose your
            inputs, review them, and start the run.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 text-sm">
          <section className="space-y-2">
            <h3 className="font-medium">Simulation rules</h3>
            <ul className="list-disc space-y-2 pl-5 text-muted-foreground">
              <li>Signals use confirmed candle closes.</li>
              <li>
                Entry is at the next candle open; exit is after{" "}
                {assumptions.holdingPeriodCandles} held candles.
              </li>
              <li>Cross-above is long; cross-below is synthetic short.</li>
              <li>Uses all hypothetical equity with one position at a time.</li>
              <li>
                Fees: {formatBasisPoints(assumptions.feeBpsPerSide)} per side;
                slippage: {formatBasisPoints(assumptions.slippageBpsPerSide)} per
                side.
              </li>
              <li>
                Overlapping signals and incomplete forward windows are skipped.
              </li>
            </ul>
          </section>

          <section className="space-y-2">
            <h3 className="font-medium">Data and limits</h3>
            <p className="text-muted-foreground">
              The server checks stored candle coverage and warm-up before the
              run. Historical analysis does not contact Binance or create live
              work.
            </p>
          </section>

          <Alert className="border-warning/50 bg-warning/10" variant="warning">
            <AlertTitle>Hypothetical only</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>
                Results are not financial advice, a prediction, or a guarantee.
                Real execution, liquidity, fees, slippage, and market behavior
                may differ.
              </p>
              <p>
                Synthetic-short results are analytical inverse exposure, not
                executable Binance Spot trades.
              </p>
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter showCloseButton />
      </DialogContent>
    </Dialog>
  );
}
