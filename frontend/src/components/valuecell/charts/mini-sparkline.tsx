import { LineChart } from "echarts/charts";
import { GridComponent } from "echarts/components";
import type { ECharts, EChartsCoreOption } from "echarts/core";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";
import { cn } from "@/lib/utils";

echarts.use([LineChart, GridComponent, CanvasRenderer]);

interface MiniSparklineProps {
  data: number[];
  color?: string;
  gradientColors?: [string, string];
  width?: number | string;
  height?: number | string;
  className?: string;
}

export function MiniSparkline({
  data,
  color = "#22c55e",
  gradientColors = ["rgba(34, 197, 94, 0.8)", "rgba(34, 197, 94, 0.1)"],
  width = 100,
  height = 40,
  className,
}: MiniSparklineProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ECharts | null>(null);

  const option: EChartsCoreOption = useMemo(() => {
    return {
      grid: {
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
      },
      xAxis: {
        type: "category",
        show: false,
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
                color: gradientColors[0],
              },
              {
                offset: 1,
                color: gradientColors[1],
              },
            ]),
          },
          animationDuration: 300,
        },
      ],
      animation: true,
    };
  }, [data, color, gradientColors]);

  useEffect(() => {
    if (!chartRef.current) return;
    chartInstance.current = echarts.init(chartRef.current);

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartInstance.current?.dispose();
    };
  }, [option]);

  useEffect(() => {
    // update chart when data changes
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
