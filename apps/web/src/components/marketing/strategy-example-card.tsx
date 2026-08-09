import { ArrowRight } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const exampleRows = [
  ["Market", "BTCUSDT"],
  ["Timeframe", "1H"],
  ["Position", "Long"],
  ["Entry", "RSI(14) crosses below 30"],
  ["Take profit", "+6%"],
  ["Stop loss", "-3%"],
  ["Maximum holding", "7 candles"],
  ["Entry execution", "Next candle open"],
] as const;

export function StrategyExampleCard() {
  return (
    <Card className="border-primary/20 bg-primary/[0.03]">
      <CardHeader>
        <CardTitle>Example strategy</CardTitle>
        <CardDescription>
          A supported configuration to make the workflow concrete.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <dl className="grid gap-3 sm:grid-cols-2">
          {exampleRows.map(([label, value]) => (
            <div className="rounded-lg border bg-background/80 p-3" key={label}>
              <dt className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                {label}
              </dt>
              <dd className="mt-1 font-medium">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="flex items-start gap-2 rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
          <ArrowRight aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
          <p>Example configuration — not a performance claim.</p>
        </div>
      </CardContent>
    </Card>
  );
}
