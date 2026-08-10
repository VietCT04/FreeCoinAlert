import {
  ArrowUpRight,
  BellRing,
  Check,
  SlidersHorizontal,
} from "lucide-react";

import {
  MARKETING_DEMO_CHART,
  MARKETING_DEMO_REPORT,
  MARKETING_DEMO_STRATEGY,
} from "@/lib/marketing/demo-strategy";

const chartGridY = [34, 78, 122, 166];
const rsiGridY = [218, 250, 282, 314];

function formatRsiPoints() {
  return MARKETING_DEMO_CHART.rsiPoints
    .map(([x, y]) => `${x},${y}`)
    .join(" ");
}

export function HeroProductDemo() {
  const entryCandle =
    MARKETING_DEMO_CHART.candles[MARKETING_DEMO_CHART.entryCandleIndex];

  return (
    <div className="marketing-homepage__demo rounded-3xl border bg-card/95 p-4 shadow-[0_1.5rem_4rem_-2rem_color-mix(in_oklch,var(--foreground)_30%,transparent)] sm:p-5">
      <div className="flex items-start justify-between gap-4 border-b pb-4">
        <div>
          <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
            Historical analysis
          </p>
          <p className="mt-2 font-heading text-xl font-semibold tracking-tight">
            {MARKETING_DEMO_STRATEGY.symbol}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {MARKETING_DEMO_STRATEGY.entry}
          </p>
        </div>
        <span className="rounded-full border bg-muted/50 px-2.5 py-1 text-xs font-semibold text-muted-foreground">
          {MARKETING_DEMO_STRATEGY.timeframe}
        </span>
      </div>

      <div
        aria-label={`Example: ${MARKETING_DEMO_STRATEGY.symbol} ${MARKETING_DEMO_STRATEGY.timeframe} strategy with an RSI entry, take profit, stop loss, and maximum holding rule.`}
        className="mt-4 overflow-hidden rounded-2xl border bg-background/70 p-2 sm:p-3"
        role="img"
      >
        <p className="sr-only">
          Example: {MARKETING_DEMO_STRATEGY.symbol} {MARKETING_DEMO_STRATEGY.timeframe} strategy with an RSI entry, take profit, stop loss, and maximum holding rule.
        </p>
        <svg
          aria-hidden="true"
          className="h-auto w-full"
          focusable="false"
          viewBox="0 0 576 338"
        >
          <g opacity="0.7">
            {chartGridY.map((y) => (
              <line
                key={`price-grid-${y}`}
                stroke="var(--border)"
                x1="16"
                x2="560"
                y1={y}
                y2={y}
              />
            ))}
            {rsiGridY.map((y) => (
              <line
                key={`rsi-grid-${y}`}
                stroke="var(--border)"
                x1="16"
                x2="560"
                y1={y}
                y2={y}
              />
            ))}
          </g>
          <line
            stroke="var(--border)"
            x1="16"
            x2="560"
            y1="194"
            y2="194"
          />
          <text
            fill="var(--muted-foreground)"
            fontSize="11"
            x="18"
            y="24"
          >
            Price
          </text>
          <text
            fill="var(--muted-foreground)"
            fontSize="11"
            x="18"
            y="212"
          >
            RSI 14
          </text>
          <line
            className="marketing-homepage__rsi-threshold"
            stroke="var(--warning)"
            strokeDasharray="4 4"
            x1="16"
            x2="560"
            y1={MARKETING_DEMO_CHART.rsiThreshold}
            y2={MARKETING_DEMO_CHART.rsiThreshold}
          />
          <text
            fill="var(--warning-foreground)"
            fontSize="10"
            x="532"
            y={MARKETING_DEMO_CHART.rsiThreshold - 6}
          >
            30
          </text>
          <polyline
            className="marketing-homepage__chart-line"
            fill="none"
            points={MARKETING_DEMO_CHART.candles
              .map((candle) => `${candle.x},${candle.close}`)
              .join(" ")}
            stroke="var(--primary)"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
          />
          {MARKETING_DEMO_CHART.candles.map((candle) => (
            <g
              className={
                candle.bullish
                  ? "marketing-homepage__candle text-success"
                  : "marketing-homepage__candle text-destructive"
              }
              key={candle.x}
            >
              <line
                stroke="currentColor"
                strokeWidth="1.5"
                x1={candle.x}
                x2={candle.x}
                y1={candle.high}
                y2={candle.low}
              />
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
          <polyline
            className="marketing-homepage__rsi-line"
            fill="none"
            points={formatRsiPoints()}
            stroke="var(--primary)"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
          />
          <g className="marketing-homepage__entry-marker">
            <line
              stroke="var(--success)"
              strokeDasharray="3 3"
              x1={entryCandle.x}
              x2={entryCandle.x}
              y1={entryCandle.close + 8}
              y2="286"
            />
            <circle
              cx={entryCandle.x}
              cy={entryCandle.close}
              fill="var(--success)"
              r="5"
            />
            <text
              fill="var(--success-foreground)"
              fontSize="11"
              fontWeight="600"
              x={entryCandle.x + 8}
              y={entryCandle.close - 10}
            >
              Entry
            </text>
          </g>
        </svg>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border bg-muted/30 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <SlidersHorizontal aria-hidden="true" className="size-4 text-primary" />
            Strategy
          </div>
          <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <div>
              <dt className="text-muted-foreground">TP</dt>
              <dd className="mt-1 font-semibold">{MARKETING_DEMO_STRATEGY.takeProfit}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">SL</dt>
              <dd className="mt-1 font-semibold">{MARKETING_DEMO_STRATEGY.stopLoss}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Max hold</dt>
              <dd className="mt-1 font-semibold">{MARKETING_DEMO_STRATEGY.maxHolding}</dd>
            </div>
          </dl>
        </div>
        <div className="marketing-homepage__report rounded-2xl border bg-muted/30 p-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Check aria-hidden="true" className="size-4 text-success" />
              Simulation report
            </div>
            <ArrowUpRight aria-hidden="true" className="size-4 text-muted-foreground" />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{MARKETING_DEMO_REPORT.label}</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            {MARKETING_DEMO_REPORT.metrics.map((metric) => (
              <div key={metric.label}>
                <p className="text-muted-foreground">{metric.label}</p>
                <p className="mt-1 font-semibold">{metric.value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
        <span className="inline-flex items-center gap-2 rounded-full bg-success/10 px-3 py-1.5 text-xs font-semibold text-success-foreground">
          <BellRing aria-hidden="true" className="size-3.5" />
          {MARKETING_DEMO_REPORT.status}
        </span>
        <span className="text-xs text-muted-foreground">Monitor entry</span>
      </div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        Illustrative product preview — not live market data.
      </p>
    </div>
  );
}
