import {
  CandlestickSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import { useEffect, useRef } from "react";
import { useGetStockHistory } from "@/api/stock";
import { useStockColors } from "@/store/settings-store";
import type { StockInterval } from "@/types/stock";

export function StockChart({
  ticker = "AAPL",
  interval = "1d",
  title,
  minHeight = 300,
  axisVisible = true,
  valueLabel,
}: {
  ticker?: string;
  interval?: StockInterval;
  title?: string;
  minHeight?: number;
  axisVisible?: boolean;
  valueLabel?: string;
}) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  // Get dynamic colors based on settings
  const { positive: upColor, negative: downColor } = useStockColors();

  // Calculate date range: last 3 months
  const endDate = new Date().toISOString().split("T")[0];
  const startDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];

  const { data: stockHistory, isLoading } = useGetStockHistory({
    ticker,
    interval,
    start_date: startDate,
    end_date: endDate,
  });

  // Initialize Chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      rightPriceScale: { visible: axisVisible, borderVisible: axisVisible },
      timeScale: { visible: axisVisible, borderVisible: axisVisible },
      grid: {
        vertLines: { visible: axisVisible },
        horzLines: { visible: axisVisible },
      },
    });

    chartRef.current = chart;

    const series = chart.addSeries(CandlestickSeries, {
      upColor: upColor,
      downColor: downColor,
      borderVisible: false,
      wickUpColor: upColor,
      wickDownColor: downColor,
    });

    seriesRef.current = series;

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [upColor, downColor, axisVisible]);

  // Update colors when settings change
  useEffect(() => {
    if (seriesRef.current) {
      seriesRef.current.applyOptions({
        upColor: upColor,
        downColor: downColor,
        wickUpColor: upColor,
        wickDownColor: downColor,
      });
    }
  }, [upColor, downColor]);

  // Update Data
  useEffect(() => {
    if (!seriesRef.current || !stockHistory?.prices) return;

    const data = stockHistory.prices
      .map((p) => ({
        time: p.timestamp.split("T")[0],
        open: p.open_price,
        high: p.high_price,
        low: p.low_price,
        close: p.close_price,
      }))
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

    const uniqueData = data.filter(
      (v, i, a) => a.findIndex((t) => t.time === v.time) === i,
    );

    seriesRef.current.setData(uniqueData);
    chartRef.current?.timeScale().fitContent();
  }, [stockHistory]);

  const hasData = !!stockHistory?.prices && stockHistory.prices.length > 0;

  return (
    <div className="relative w-full" style={{ minHeight }}>
      {title && (
        <div className="absolute top-2 left-2 z-10 rounded bg-white/60 px-2 py-1 font-semibold text-neutral-700 text-xs">
          {title}
        </div>
      )}
      {isLoading && (
        <div className="absolute top-2 right-2 z-10 text-gray-500 text-xs">
          Loading...
        </div>
      )}
      {!isLoading && valueLabel && (
        <div className="absolute top-2 right-2 z-10 rounded bg-white/70 px-2 py-1 font-semibold text-neutral-700 text-xs">
          {valueLabel}
        </div>
      )}
      {!isLoading && !hasData && (
        <div className="absolute inset-0 z-10 flex items-center justify-center text-gray-400 text-sm">
          No chart data
        </div>
      )}
      <div
        ref={chartContainerRef}
        className="w-full"
        style={{ height: minHeight }}
      />
    </div>
  );
}
