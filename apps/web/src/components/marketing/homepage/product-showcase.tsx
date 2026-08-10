import Link from "next/link";
import { ArrowUpRight, Check, ShieldCheck } from "lucide-react";

import {
  MARKETING_DEMO_CHART,
  MARKETING_DEMO_REPORT,
  MARKETING_DEMO_STRATEGY,
} from "@/lib/marketing/demo-strategy";

import { homepageExampleLinks } from "./constants";

const reportCategories = [
  "Trades",
  "Net return",
  "Maximum drawdown",
  "Win rate",
  "Profit factor",
  "Equity curve",
  "Exit reasons",
] as const;

const entryCapabilities = [
  "RSI(14) threshold cross",
  "Price / SMA(200) cross",
] as const;

const exitCapabilities = [
  "Take profit",
  "Stop loss",
  "RSI exit where supported",
  "Maximum holding candles",
] as const;

const timeframes = ["1h", "4h"] as const;

function PreviewChart() {
  const entryCandle = MARKETING_DEMO_CHART.candles[MARKETING_DEMO_CHART.entryCandleIndex];

  return (
    <svg
      aria-hidden="true"
      className="h-auto w-full"
      role="presentation"
      viewBox="0 0 576 338"
    >
      <g opacity="0.7">
        {[34, 78, 122, 166, 218, 250, 282, 314].map((y) => (
          <line key={y} stroke="var(--border)" x1="16" x2="560" y1={y} y2={y} />
        ))}
      </g>
      <line stroke="var(--border)" x1="16" x2="560" y1="194" y2="194" />
      <line
        stroke="var(--muted-foreground)"
        strokeDasharray="4 4"
        x1="16"
        x2="560"
        y1={MARKETING_DEMO_CHART.rsiThreshold}
        y2={MARKETING_DEMO_CHART.rsiThreshold}
      />
      <polyline
        fill="none"
        points={MARKETING_DEMO_CHART.candles.map((candle) => `${candle.x},${candle.close}`).join(" ")}
        stroke="var(--primary)"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <g>
        {MARKETING_DEMO_CHART.candles.map((candle) => (
          <g className={candle.bullish ? "text-success" : "text-destructive"} key={candle.x}>
            <line stroke="currentColor" strokeWidth="1.5" x1={candle.x} x2={candle.x} y1={candle.high} y2={candle.low} />
            <rect
              fill="currentColor"
              height={Math.max(Math.abs(candle.open - candle.close), 5)}
              rx="1"
              width="10"
              x={candle.x - 5}
              y={Math.min(candle.open, candle.close)}
            />
          </g>
        ))}
      </g>
      <polyline
        fill="none"
        points={MARKETING_DEMO_CHART.rsiPoints.map(([x, y]) => `${x},${y}`).join(" ")}
        stroke="var(--primary)"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <line stroke="var(--success)" strokeDasharray="3 3" x1={entryCandle.x} x2={entryCandle.x} y1={entryCandle.close + 8} y2="286" />
      <circle cx={entryCandle.x} cy={entryCandle.close} fill="var(--success)" r="5" />
      <text fill="var(--success-foreground)" fontSize="11" fontWeight="600" x={entryCandle.x + 8} y={entryCandle.close - 10}>
        Entry
      </text>
      <text fill="var(--muted-foreground)" fontSize="10" x="532" y={MARKETING_DEMO_CHART.rsiThreshold - 6}>
        RSI 30
      </text>
    </svg>
  );
}

function CapabilityGroup({ items, label }: { items: readonly string[]; label: string }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{label}</p>
      <ul className="space-y-2 text-sm">
        {items.map((item) => (
          <li className="flex items-start gap-2" key={item}>
            <Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ProductShowcase() {
  return (
    <section
      aria-labelledby="product-showcase-title"
      className="scroll-mt-24 border-b bg-muted/30 py-20 sm:py-24"
      id="product-showcase"
    >
      <div className="mx-auto w-full max-w-6xl space-y-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl space-y-3">
          <p className="text-sm font-semibold tracking-[0.18em] text-muted-foreground uppercase">
            Product preview
          </p>
          <h2
            className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl"
            id="product-showcase-title"
          >
            See the strategy and the report together
          </h2>
          <p className="text-base leading-7 text-muted-foreground sm:text-lg">
            Start with a concrete configuration, then inspect the categories
            and assumptions that give a historical result meaning.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-start">
          <div className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
            <div className="flex items-start justify-between gap-4 border-b pb-5">
              <div>
                <p className="text-sm font-semibold text-primary">Example strategy</p>
                <h3 className="mt-2 font-heading text-2xl font-semibold">{MARKETING_DEMO_STRATEGY.symbol}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{MARKETING_DEMO_STRATEGY.entry}</p>
              </div>
              <span className="rounded-full border px-3 py-1 text-xs font-semibold text-muted-foreground">
                {MARKETING_DEMO_STRATEGY.timeframe}
              </span>
            </div>

            <dl className="mt-6 grid gap-3 sm:grid-cols-2">
              {[
                ["Market", MARKETING_DEMO_STRATEGY.symbol],
                ["Timeframe", MARKETING_DEMO_STRATEGY.timeframe],
                ["Position", "Long"],
                ["Entry", MARKETING_DEMO_STRATEGY.entry],
                ["Take profit", MARKETING_DEMO_STRATEGY.takeProfit],
                ["Stop loss", MARKETING_DEMO_STRATEGY.stopLoss],
                ["Maximum holding", MARKETING_DEMO_STRATEGY.maxHolding],
                ["Entry execution", "Next candle open"],
              ].map(([label, value]) => (
                <div className="rounded-xl border bg-background/70 p-3" key={label}>
                  <dt className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</dt>
                  <dd className="mt-1 text-sm font-medium">{value}</dd>
                </div>
              ))}
            </dl>

            <div className="mt-6 grid gap-6 border-t pt-6 sm:grid-cols-2">
              <CapabilityGroup items={entryCapabilities} label="Entries" />
              <CapabilityGroup items={exitCapabilities} label="Exits" />
              <CapabilityGroup items={timeframes} label="Timeframes" />
            </div>
          </div>

          <div className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
            <div className="flex items-start gap-3">
              <ShieldCheck aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-primary" />
              <div>
                <p className="text-sm font-semibold text-primary">{MARKETING_DEMO_REPORT.label}</p>
                <h3 className="mt-1 font-heading text-2xl font-semibold">A report built for context</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  The preview shows report categories without inventing
                  performance numbers.
                </p>
              </div>
            </div>

            <div className="mt-6 overflow-hidden rounded-xl border bg-background/80 p-3 sm:p-5">
              <div className="mb-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                <span>{MARKETING_DEMO_STRATEGY.symbol} · {MARKETING_DEMO_STRATEGY.timeframe}</span>
                <span>Hypothetical equity</span>
              </div>
              <PreviewChart />
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {reportCategories.map((category) => (
                <div className="rounded-xl border bg-background/70 p-3" key={category}>
                  <p className="text-xs leading-5 text-muted-foreground">{category}</p>
                  <p className="mt-1 text-sm font-semibold">Included</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-6 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Explore examples:</span>
          {homepageExampleLinks.map((link) => (
            <Link className="inline-flex items-center gap-1 underline-offset-4 hover:text-foreground hover:underline" href={link.href} key={link.href}>
              {link.label}
              <ArrowUpRight aria-hidden="true" className="size-3.5" />
            </Link>
          ))}
        </div>

        <p className="text-sm leading-6 text-muted-foreground">
          <span className="font-medium text-foreground">Illustrative product preview</span> — not live market data and not a performance claim.
        </p>
      </div>
    </section>
  );
}
