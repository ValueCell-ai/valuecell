import {
  BarChart,
  CandlestickChart as ECandlestickChart,
  LineChart,
} from "echarts/charts";
import {
  AxisPointerComponent,
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
import { cn } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";

// Register ECharts components
echarts.use([
  BarChart,
  ECandlestickChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  AxisPointerComponent,
  DataZoomComponent,
  CanvasRenderer,
]);

export interface CandlestickData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface CandlestickChartProps {
  data: CandlestickData[];
  width?: number | string;
  height?: number | string;
  className?: string;
  loading?: boolean;
  showVolume?: boolean;
}

function CandlestickChart({
  data,
  width = "100%",
  height = 500,
  className,
  loading,
  showVolume = true,
}: CandlestickChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ECharts | null>(null);
  const stockColors = useStockColors();

  const option: EChartsOption = useMemo(() => {
    if (!data || data.length === 0) return {};

    const dates = data.map((item) => item.time);
    const ohlcData = data.map((item) => [
      item.open,
      item.close,
      item.low,
      item.high,
    ]);
    const volumes = data.map((item, index) => [
      index,
      item.volume,
      item.close >= item.open ? 1 : -1, // 1 = up (positive), -1 = down (negative)
    ]);

    const mainGridHeight = showVolume ? "50%" : "75%";
    const volumeGridTop = showVolume ? "63%" : undefined;

    const series: EChartsOption["series"] = [
      {
        name: "K-Line",
        type: "candlestick",
        data: ohlcData,
        itemStyle: {
          color: stockColors.positive, // up candle fill
          color0: stockColors.negative, // down candle fill
          borderColor: stockColors.positive, // up candle border
          borderColor0: stockColors.negative, // down candle border
        },
      },
    ];

    if (showVolume) {
      series.push({
        name: "Volume",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: {
          color: (params) => {
            const value = params.value as [number, number, number];
            // value[2]: 1 = up (positive color), -1 = down (negative color)
            return value[2] === 1 ? stockColors.positive : stockColors.negative;
          },
        },
      });
    }

    const grids: Array<{
      left: string;
      right: string;
      height: string;
      top?: string;
    }> = [
      {
        left: "10%",
        right: "8%",
        height: mainGridHeight,
      },
    ];

    const xAxes: Array<{
      type: "category";
      data: string[];
      boundaryGap: boolean;
      axisLine: { onZero: boolean };
      splitLine: { show: boolean };
      min: string;
      max: string;
      axisPointer?: { z: number };
      gridIndex?: number;
      axisTick?: { show: boolean };
      axisLabel?: { show: boolean };
    }> = [
      {
        type: "category",
        data: dates,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: "dataMin",
        max: "dataMax",
        axisPointer: { z: 100 },
      },
    ];

    const yAxes: Array<{
      scale: boolean;
      splitArea?: { show: boolean };
      gridIndex?: number;
      splitNumber?: number;
      axisLabel?: { show: boolean };
      axisLine?: { show: boolean };
      axisTick?: { show: boolean };
      splitLine?: { show: boolean };
    }> = [
      {
        scale: true,
        splitArea: { show: true },
      },
    ];

    if (showVolume) {
      grids.push({
        left: "10%",
        right: "8%",
        top: volumeGridTop,
        height: "16%",
      });

      xAxes.push({
        type: "category",
        gridIndex: 1,
        data: dates,
        boundaryGap: false,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: "dataMin",
        max: "dataMax",
      });

      yAxes.push({
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
      });
    }

    return {
      animation: false,
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        borderWidth: 1,
        borderColor: "#ccc",
        padding: 10,
        textStyle: { color: "#000" },
        position: (
          pos: number[],
          _params: unknown,
          _el: unknown,
          _rect: unknown,
          size: { viewSize: number[] },
        ) => {
          const obj: Record<string, number> = { top: 10 };
          obj[["left", "right"][+(pos[0] < size.viewSize[0] / 2)]] = 30;
          return obj;
        },
      },
      axisPointer: {
        link: [{ xAxisIndex: "all" }],
        label: { backgroundColor: "#777" },
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: showVolume ? [0, 1] : [0],
          start: 50,
          end: 100,
        },
        {
          show: true,
          xAxisIndex: showVolume ? [0, 1] : [0],
          type: "slider",
          top: "85%",
          start: 50,
          end: 100,
        },
      ],
      series,
    };
  }, [data, stockColors, showVolume]);

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
    if (chartInstance.current) {
      chartInstance.current.setOption(option);
    }
  }, [option]);

  useEffect(() => {
    if (chartInstance.current) {
      if (loading) {
        chartInstance.current.showLoading();
      } else {
        chartInstance.current.hideLoading();
      }
    }
  }, [loading]);

  return (
    <div
      ref={chartRef}
      className={cn("w-fit", className)}
      style={{ width, height }}
    />
  );
}

export default CandlestickChart;
