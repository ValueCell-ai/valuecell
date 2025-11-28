import { CandlestickChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
} from "echarts/components";
import type { ECharts } from "echarts/core";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts/types/dist/shared";
import { useEffect, useMemo, useRef } from "react";
import { useChartResize } from "@/hooks/use-chart-resize";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type { KLineData } from "@/types/chart";

echarts.use([
  CandlestickChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  CanvasRenderer,
]);

interface KLineChartProps {
  data: KLineData;
  width?: number | string;
  height?: number | string;
  className?: string;
}

function KLineChart({
  data,
  width = "100%",
  height = 400,
  className,
}: KLineChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ECharts | null>(null);
  const stockColors = useStockColors();

  const upColor = stockColors["positive"];
  const downColor = stockColors["negative"];

  const option: EChartsOption = useMemo(() => {
    return {
      grid: { left: 8, right: 8, top: 10, bottom: 40 },
      xAxis: {
        type: "category",
        data: data.categories,
        axisLabel: {
          formatter: (value: string) =>
            TimeUtils.formatUTC(value, TIME_FORMATS.MODAL_TRADE_TIME),
        },
        axisLine: { show: true },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        scale: true,
        splitLine: {
          show: true,
        },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return "";
          const p = params[0] as {
            axisValue: string;
            value: [number, number, number, number];
          };
          const date = TimeUtils.formatUTC(
            p.axisValue,
            TIME_FORMATS.MODAL_TRADE_TIME,
          );
          const [open, close, low, high] = p.value;
          return `<div style="font-weight:600;margin-bottom:6px">${date}</div>
          <div>Open: <strong>${open.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></div>
          <div>High: <strong>${high.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></div>
          <div>Low: <strong>${low.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></div>
          <div>Close: <strong>${close.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></div>`;
        },
      },
      dataZoom: [
        { type: "inside", start: 0, end: 100 },
        { start: 0, end: 100 },
      ],
      series: [
        {
          type: "candlestick",
          data: data.values,
          itemStyle: {
            color: upColor,
            color0: downColor,
            borderColor: upColor,
            borderColor0: downColor,
          },
        },
      ],
      animation: true,
    };
  }, [data, upColor, downColor]);

  useChartResize(chartInstance);

  useEffect(() => {
    if (!chartRef.current) return;
    chartInstance.current = echarts.init(chartRef.current);
    chartInstance.current.setOption(option);
    return () => {
      chartInstance.current?.dispose();
    };
  }, [option]);

  useEffect(() => {
    if (!chartInstance.current) return;
    chartInstance.current.setOption({
      xAxis: { data: data.categories },
      series: [{ data: data.values }],
    });
  }, [data]);

  return (
    <div
      ref={chartRef}
      className={cn("w-fit", className)}
      style={{ width, height }}
    />
  );
}

export default KLineChart;
