import { LineChart } from "echarts/charts";
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
import { STOCK_COLORS, STOCK_GRADIENT_COLORS } from "@/constants/stock";
import { useChartResize } from "@/hooks/use-chart-resize";
import { format } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { SparklineData } from "@/types/chart";
import type { StockChangeType } from "@/types/stock";

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  CanvasRenderer,
]);

interface SparklineProps {
  data: SparklineData;
  changeType: StockChangeType;
  width?: number | string;
  height?: number | string;
  className?: string;
}

function Sparkline({
  data,
  changeType,
  width = "100%",
  height = 400,
  className,
}: SparklineProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ECharts | null>(null);

  // Get colors based on change type
  const color = STOCK_COLORS[changeType];
  const gradientColors = STOCK_GRADIENT_COLORS[changeType];

  const option: EChartsOption = useMemo(() => {
    return {
      grid: {
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
      },
      xAxis: {
        type: "time",
        show: false,
        axisLabel: {
          show: false,
        },
      },
      yAxis: {
        type: "value",
        scale: true,
        splitLine: {
          show: true,
          lineStyle: {
            color: "rgba(174, 174, 174, 0.5)",
            opacity: 0.3,
            type: "solid",
          },
        },
      },
      series: [
        {
          type: "line",
          data: data,
          symbol: "circle",
          symbolSize: 12,
          showSymbol: false,
          itemStyle: {
            color: color,
            borderColor: "#fff",
            borderWidth: 4,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              {
                offset: 0,
                color: gradientColors[0],
              },
              {
                offset: 1,
                color: gradientColors[1],
              },
            ]),
          },
          animationDuration: 500,
          animationEasing: "quadraticOut",
        },
      ],
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(0, 0, 0, 0.7)",
        textStyle: {
          color: "#fff",
          fontSize: 12,
        },
        padding: [14, 16],
        borderRadius: 12,
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return "";

          const param = params[0] as { data: [number, number] };
          if (!param || !param.data) return "";

          const timestamp = param.data[0];
          const value = param.data[1];

          // Use our time utility for formatting
          const formatDate = format(timestamp, "MMM D");
          const formatTime = format(timestamp, "h:mm:ss A");

          return `
            <div style="font-weight: 500; font-size: 12px; margin-bottom: 8px; letter-spacing: -0.42px;">
              ${formatDate}, ${formatTime}
            </div>
            <div style="font-weight: bold; font-size: 18px; font-family: 'SF Pro Display', sans-serif;">
              ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          `;
        },
        axisPointer: {
          type: "none",
        },
      },
    };
  }, [data, color, gradientColors]);

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
      chartInstance.current.setOption({
        series: [{ data }],
      });
    }
  }, [data]);

  return (
    <div
      ref={chartRef}
      className={cn("w-fit", className)}
      style={{ width, height }}
    />
  );
}

export default Sparkline;
