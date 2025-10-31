import { LineChart } from "echarts/charts";
import { GridComponent } from "echarts/components";
import type { ECharts, EChartsCoreOption } from "echarts/core";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";
import { useChartResize } from "@/hooks/use-chart-resize";
import { cn } from "@/lib/utils";
import { useStockColors, useStockGradientColors } from "@/store/settings-store";
import type { SparklineData } from "@/types/chart";
import type { StockChangeType } from "@/types/stock";

echarts.use([LineChart, GridComponent, CanvasRenderer]);

interface MiniSparklineProps {
  data: SparklineData;
  changeType: StockChangeType;
  width?: number | string;
  height?: number | string;
  className?: string;
}

function MiniSparkline({
  data,
  changeType,
  width = 100,
  height = 40,
  className,
}: MiniSparklineProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ECharts | null>(null);
  const stockColors = useStockColors();
  const gradientColors = useStockGradientColors();

  useChartResize(chartInstance);

  const color = stockColors[changeType];
  const gradient = gradientColors[changeType];

  const option: EChartsCoreOption = useMemo(() => {
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
        show: false,
        scale: true,
      },
      series: [
        {
          type: "line",
          data: data,
          symbol: "none",
          lineStyle: {
            color: color,
            width: 1.5,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              {
                offset: 0,
                color: gradient[0],
              },
              {
                offset: 1,
                color: gradient[1],
              },
            ]),
          },
          animationDuration: 300,
        },
      ],
      animation: true,
    };
  }, [data, color, gradient]);

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

export default MiniSparkline;
