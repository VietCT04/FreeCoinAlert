"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Maximize2 } from "lucide-react";
import type {
  CandlestickData,
  SeriesMarker,
  UTCTimestamp,
} from "lightweight-charts";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import type {
  HistoricalAnalysisCandlePreview,
  HistoricalAnalysisTradeMarker,
} from "./types";

type CandleChartProps = {
  candles: HistoricalAnalysisCandlePreview[];
  exchange: string;
  marketType: string;
  markers: HistoricalAnalysisTradeMarker[];
  symbol: string;
  timeframe: string;
};

const MAX_CHART_PRICE_SCALE_DIGITS = 8;

type PlotData = {
  candles: CandlestickData<UTCTimestamp>[];
  markers: SeriesMarker<UTCTimestamp>[];
  fractionDigits: number;
};

function numericPrice(value: string): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function utcTimestamp(value: string): UTCTimestamp | null {
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) {
    return null;
  }

  return Math.floor(milliseconds / 1000) as UTCTimestamp;
}

function decimalPlaces(value: string): number {
  const fraction = value.split(".")[1];
  return fraction ? fraction.length : 0;
}

function formatPrice(value: number, fractionDigits: number): string {
  return value
    .toFixed(fractionDigits)
    .replace(/(\.\d*?[1-9])0+$/, "$1")
    .replace(/\.0+$/, "")
    .replace(/^-0$/, "0");
}

function buildPlotData(
  candles: HistoricalAnalysisCandlePreview[],
  markers: HistoricalAnalysisTradeMarker[],
): PlotData {
  const values = candles.flatMap((candle) => [
    candle.openPrice,
    candle.highPrice,
    candle.lowPrice,
    candle.closePrice,
  ]);
  const fractionDigits = Math.min(
    MAX_CHART_PRICE_SCALE_DIGITS,
    Math.max(
      2,
      ...values.map(decimalPlaces),
      ...markers.map((marker) => decimalPlaces(marker.price)),
    ),
  );
  const plottedCandles = candles.flatMap((candle) => {
    const time = utcTimestamp(candle.candleOpenTime);
    const open = numericPrice(candle.openPrice);
    const high = numericPrice(candle.highPrice);
    const low = numericPrice(candle.lowPrice);
    const close = numericPrice(candle.closePrice);
    if (
      time === null ||
      open === null ||
      high === null ||
      low === null ||
      close === null
    ) {
      return [];
    }

    return [{ time, open, high, low, close }];
  });
  const candleTimes = new Set(plottedCandles.map((candle) => Number(candle.time)));
  const plottedMarkers = markers.flatMap((marker): SeriesMarker<UTCTimestamp>[] => {
    const time = utcTimestamp(marker.candleOpenTime);
    const price = numericPrice(marker.price);
    if (time === null || price === null || !candleTimes.has(Number(time))) {
      return [];
    }

    const isBuy = marker.side === "buy";
    return [
      {
        time,
        position: isBuy ? "atPriceBottom" : "atPriceTop",
        color: isBuy ? "#16a34a" : "#dc2626",
        shape: isBuy ? "arrowUp" : "arrowDown",
        text: isBuy ? "Buy" : "Sell",
        price,
      },
    ];
  });

  return {
    candles: plottedCandles,
    markers: plottedMarkers.sort((left, right) => Number(left.time) - Number(right.time)),
    fractionDigits,
  };
}

function ChartLegend({ tradeCount }: { tradeCount: number }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
      <span>
        <span className="font-semibold text-green-600">Buy</span> · long entry or
        synthetic-short exit
      </span>
      <span>
        <span className="font-semibold text-red-600">Sell</span> · long exit or
        synthetic-short entry
      </span>
      <span>{tradeCount} hypothetical trades shown</span>
    </div>
  );
}

export function CandleChart({
  candles,
  exchange,
  marketType,
  markers,
  symbol,
  timeframe,
}: CandleChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [chartError, setChartError] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const plotData = useMemo(() => buildPlotData(candles, markers), [candles, markers]);

  useEffect(() => {
    setChartError(false);
    const container = chartContainerRef.current;
    if (!container || plotData.candles.length === 0) {
      return;
    }

    let disposed = false;
    let chart: { remove: () => void } | null = null;
    let seriesMarkers: { detach: () => void } | null = null;
    let resizeObserver: ResizeObserver | null = null;
    const initialHeight = isExpanded ? 560 : 360;

    void import("lightweight-charts")
      .then(({ CandlestickSeries, createChart, createSeriesMarkers }) => {
        if (disposed) {
          return;
        }

        const nextChart = createChart(container, {
          width: Math.max(container.clientWidth, 320),
          height: Math.max(container.clientHeight, initialHeight),
          layout: {
            background: { type: "solid", color: "transparent" },
            attributionLogo: true,
            textColor: "#64748b",
          },
          grid: {
            vertLines: { color: "rgba(148, 163, 184, 0.16)" },
            horzLines: { color: "rgba(148, 163, 184, 0.16)" },
          },
          rightPriceScale: {
            borderColor: "rgba(148, 163, 184, 0.35)",
            scaleMargins: { top: 0.12, bottom: 0.12 },
          },
          timeScale: {
            borderColor: "rgba(148, 163, 184, 0.35)",
            timeVisible: true,
            secondsVisible: false,
          },
        });
        chart = nextChart;

        const series = nextChart.addSeries(CandlestickSeries, {
          upColor: "#16a34a",
          downColor: "#dc2626",
          borderUpColor: "#16a34a",
          borderDownColor: "#dc2626",
          wickUpColor: "#16a34a",
          wickDownColor: "#dc2626",
          priceFormat: {
            type: "custom",
            // API decimals may preserve storage scale (up to 18 places). A
            // smaller tick makes Lightweight Charts derive an invalid base;
            // the formatter below still preserves meaningful small prices.
            minMove:
              10 **
              -Math.min(plotData.fractionDigits, MAX_CHART_PRICE_SCALE_DIGITS),
            formatter: (price: number) =>
              formatPrice(price, plotData.fractionDigits),
          },
        });
        series.setData(plotData.candles);
        seriesMarkers = createSeriesMarkers(series, plotData.markers);
        nextChart.timeScale().fitContent();

        resizeObserver = new ResizeObserver((entries) => {
          const width = Math.max(
            entries[0]?.contentRect.width ?? container.clientWidth,
            320,
          );
          const height = Math.max(entries[0]?.contentRect.height ?? 0, 320);
          if (width > 0) {
            nextChart.applyOptions({ width, height });
          }
        });
        resizeObserver.observe(container);
      })
      .catch(() => {
        if (!disposed) {
          setChartError(true);
        }
      });

    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      seriesMarkers?.detach();
      chart?.remove();
    };
  }, [isExpanded, plotData]);

  if (plotData.candles.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Price candles are not available for this report.
      </p>
    );
  }

  const tradeCount = Math.floor(plotData.markers.length / 2);
  const chartLabel = `Candlestick chart for ${symbol} with ${tradeCount} hypothetical trades and buy and sell markers`;
  const chartCanvas = (
    <div
      aria-label={chartLabel}
      className={
        isExpanded
          ? "h-full min-h-[320px] w-full overflow-hidden rounded-xl border bg-card p-2 sm:p-4"
          : "min-h-[360px] w-full overflow-hidden rounded-xl border bg-card p-2 sm:p-4"
      }
      ref={chartContainerRef}
      role="img"
    >
      {chartError ? (
        <p className="p-4 text-sm text-muted-foreground">
          The price chart is temporarily unavailable.
        </p>
      ) : null}
    </div>
  );

  return (
    <figure aria-labelledby="historical-analysis-candle-chart-title" className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold tracking-tight">{symbol}</h3>
          <p className="text-xs text-muted-foreground">
            {exchange} {marketType} · {timeframe}
          </p>
        </div>
        <Button
          aria-expanded={isExpanded}
          aria-label={`Expand ${symbol} chart`}
          onClick={() => setIsExpanded(true)}
          size="sm"
          type="button"
          variant="outline"
        >
          <Maximize2 aria-hidden="true" />
          <span>Expand chart</span>
        </Button>
      </div>
      {isExpanded ? (
        <Dialog open={isExpanded} onOpenChange={setIsExpanded}>
          <DialogContent className="h-[90vh] w-[calc(100%-2rem)] max-w-[1600px] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden p-4 sm:max-w-[1600px]">
            <DialogHeader className="pr-8">
              <DialogTitle>{symbol} · {timeframe}</DialogTitle>
              <DialogDescription>
                {exchange} {marketType} · stored candles and hypothetical trade markers
              </DialogDescription>
            </DialogHeader>
            <div className="h-full min-h-0">{chartCanvas}</div>
            <ChartLegend tradeCount={tradeCount} />
          </DialogContent>
        </Dialog>
      ) : (
        <>
          {chartCanvas}
          <ChartLegend tradeCount={tradeCount} />
        </>
      )}
      <figcaption className="text-sm text-muted-foreground" id="historical-analysis-candle-chart-title">
        Stored candles with hypothetical order markers. Drag or scroll to inspect
        the selected range; no live orders are placed.
      </figcaption>
    </figure>
  );
}
