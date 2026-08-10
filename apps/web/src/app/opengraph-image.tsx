import { ImageResponse } from "next/og";

import {
  MARKETING_DEMO_CHART,
  MARKETING_DEMO_STRATEGY,
} from "@/lib/marketing/demo-strategy";

const colors = {
  background: "#111111",
  card: "#1b1b1b",
  chart: "#121212",
  border: "#3a3a3a",
  grid: "#303030",
  primary: "#f4f4f0",
  secondary: "#b7b7b0",
  muted: "#77776f",
  green: "#66c28a",
  greenText: "#a9e7bd",
  red: "#d97373",
  amber: "#d3ae67",
} as const;

const chartGridY = [34, 78, 122, 166, 218, 250, 282, 314] as const;
const chartGridX = [48, 128, 208, 288, 368, 448, 528] as const;

export const alt =
  "FreeCoinAlert crypto strategy backtesting product preview with an XRPUSDT RSI strategy";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

function MiniChart() {
  const entryCandle =
    MARKETING_DEMO_CHART.candles[MARKETING_DEMO_CHART.entryCandleIndex];

  return (
    <svg
      aria-hidden="true"
      height="220"
      viewBox="0 0 576 338"
      width="500"
    >
      {chartGridY.map((y) => (
        <line
          key={`horizontal-${y}`}
          stroke={colors.grid}
          strokeWidth="1"
          x1="16"
          x2="560"
          y1={y}
          y2={y}
        />
      ))}
      {chartGridX.map((x) => (
        <line
          key={`vertical-${x}`}
          stroke={colors.grid}
          strokeWidth="1"
          x1={x}
          x2={x}
          y1="16"
          y2="326"
        />
      ))}
      <line
        stroke={colors.border}
        strokeWidth="1"
        x1="16"
        x2="560"
        y1="194"
        y2="194"
      />
      <line
        stroke={colors.amber}
        strokeDasharray="5 5"
        strokeWidth="1.5"
        x1="16"
        x2="560"
        y1={MARKETING_DEMO_CHART.rsiThreshold}
        y2={MARKETING_DEMO_CHART.rsiThreshold}
      />
      <polyline
        fill="none"
        points={MARKETING_DEMO_CHART.candles
          .map((candle) => `${candle.x},${candle.close}`)
          .join(" ")}
        stroke={colors.primary}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      {MARKETING_DEMO_CHART.candles.map((candle) => {
        const candleColor = candle.bullish ? colors.green : colors.red;

        return (
          <g key={candle.x}>
            <line
              stroke={candleColor}
              strokeWidth="1.5"
              x1={candle.x}
              x2={candle.x}
              y1={candle.high}
              y2={candle.low}
            />
            <rect
              fill={candleColor}
              height={Math.max(Math.abs(candle.open - candle.close), 5)}
              rx="1"
              width="10"
              x={candle.x - 5}
              y={Math.min(candle.open, candle.close)}
            />
          </g>
        );
      })}
      <polyline
        fill="none"
        points={MARKETING_DEMO_CHART.rsiPoints
          .map(([x, y]) => `${x},${y}`)
          .join(" ")}
        stroke={colors.secondary}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
      <line
        stroke={colors.green}
        strokeDasharray="4 4"
        strokeWidth="1.5"
        x1={entryCandle.x}
        x2={entryCandle.x}
        y1={entryCandle.close + 8}
        y2="326"
      />
      <circle
        cx={entryCandle.x}
        cy={entryCandle.close}
        fill={colors.green}
        r="6"
      />
    </svg>
  );
}

function StrategyChip({ children }: { children: string }) {
  return (
    <div
      style={{
        background: "#252525",
        border: `1px solid ${colors.border}`,
        borderRadius: 999,
        color: colors.secondary,
        display: "flex",
        fontSize: 18,
        padding: "10px 15px",
      }}
    >
      {children}
    </div>
  );
}

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: colors.background,
          color: colors.primary,
          display: "flex",
          flexDirection: "column",
          height: "100%",
          padding: "58px 64px",
          width: "100%",
        }}
      >
        <div
          style={{
            alignItems: "center",
            display: "flex",
            gap: 14,
          }}
        >
          <div
            style={{
              alignItems: "center",
              background: colors.primary,
              borderRadius: 12,
              color: colors.background,
              display: "flex",
              fontSize: 20,
              fontWeight: 800,
              height: 42,
              justifyContent: "center",
              width: 42,
            }}
          >
            FC
          </div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>FreeCoinAlert</div>
        </div>

        <div
          style={{
            display: "flex",
            flex: 1,
            gap: 52,
            marginTop: 30,
          }}
        >
          <div
            style={{
              display: "flex",
              flex: 1,
              flexDirection: "column",
              justifyContent: "center",
              paddingBottom: 12,
            }}
          >
            <div
              style={{
                color: colors.secondary,
                fontSize: 17,
                fontWeight: 700,
                letterSpacing: "0.16em",
              }}
            >
              CRYPTO STRATEGY BACKTESTING
            </div>
            <div
              style={{
                fontSize: 53,
                fontWeight: 750,
                letterSpacing: "-0.035em",
                lineHeight: 1.08,
                marginTop: 20,
              }}
            >
              <div>Backtest a crypto</div>
              <div>strategy before you trust it.</div>
            </div>
            <div
              style={{
                color: colors.secondary,
                fontSize: 23,
                lineHeight: 1.35,
                marginTop: 22,
                maxWidth: 450,
              }}
            >
              Define the rules. Test them. Get alerted when the entry appears
              again.
            </div>
            <div
              style={{
                alignItems: "center",
                color: colors.primary,
                display: "flex",
                fontSize: 19,
                fontWeight: 650,
                gap: 10,
                marginTop: 36,
              }}
            >
              Backtest
              <span style={{ color: colors.muted }}>→</span>
              Understand
              <span style={{ color: colors.muted }}>→</span>
              Alert
            </div>
          </div>

          <div
            style={{
              background: colors.card,
              border: `1px solid ${colors.border}`,
              borderRadius: 22,
              display: "flex",
              flex: 1.05,
              flexDirection: "column",
              padding: "23px 24px 20px",
            }}
          >
            <div
              style={{
                alignItems: "center",
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ fontSize: 28, fontWeight: 750 }}>
                  {MARKETING_DEMO_STRATEGY.symbol}
                </div>
                <div style={{ color: colors.secondary, fontSize: 17 }}>
                  {MARKETING_DEMO_STRATEGY.entry}
                </div>
              </div>
              <div
                style={{
                  border: `1px solid ${colors.border}`,
                  borderRadius: 999,
                  color: colors.secondary,
                  display: "flex",
                  fontSize: 17,
                  padding: "8px 13px",
                }}
              >
                {MARKETING_DEMO_STRATEGY.timeframe}
              </div>
            </div>
            <div
              style={{
                background: colors.chart,
                border: `1px solid ${colors.border}`,
                borderRadius: 16,
                display: "flex",
                marginTop: 16,
                overflow: "hidden",
                padding: "4px 8px",
              }}
            >
              <MiniChart />
            </div>
            <div
              style={{
                display: "flex",
                gap: 8,
                marginTop: 14,
              }}
            >
              <StrategyChip>TP {MARKETING_DEMO_STRATEGY.takeProfit}</StrategyChip>
              <StrategyChip>SL {MARKETING_DEMO_STRATEGY.stopLoss}</StrategyChip>
              <StrategyChip>Max {MARKETING_DEMO_STRATEGY.maxHolding}</StrategyChip>
            </div>
            <div
              style={{
                alignItems: "center",
                color: colors.greenText,
                display: "flex",
                fontSize: 17,
                fontWeight: 700,
                gap: 8,
                marginTop: 12,
              }}
            >
              <span style={{ color: colors.green }}>●</span>
              Entry condition defined
            </div>
          </div>
        </div>
      </div>
    ),
    size,
  );
}
