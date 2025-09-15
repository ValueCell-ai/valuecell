import { LineChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
} from "echarts/components";
import type { ECharts, EChartsCoreOption } from "echarts/core";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";
import { cn } from "@/lib/utils";

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  CanvasRenderer,
]);

interface DataPoint {
  timestamp: string; // ISO 日期字符串或时间戳
  value: number;
}

interface SparklineProps {
  data: DataPoint[];
  color?: string;
  gradientColors?: [string, string];
  width?: number | string;
  height?: number | string;
  className?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
  yAxisRange?: [number, number];
  formatTooltip?: (value: number, timestamp: string) => string;
}

function Sparkline({
  data,
  color = "#41C3A9",
  gradientColors = ["rgba(65, 195, 169, 0.6)", "rgba(65, 195, 169, 0)"],
  width = "100%",
  height = 400,
  className,
  showGrid = true,
  showTooltip = true,
  yAxisRange,
  formatTooltip,
}: SparklineProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ECharts | null>(null);

  // 处理数据格式
  const chartData = useMemo(() => {
    return data.map((item) => [item.timestamp, item.value]);
  }, [data]);

  // 计算Y轴范围
  const calculatedYRange = useMemo(() => {
    if (yAxisRange) return yAxisRange;

    const values = data.map((item) => item.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1; // 10% 的填充

    return [Math.max(0, min - padding), max + padding];
  }, [data, yAxisRange]);

  const option: EChartsCoreOption = useMemo(() => {
    return {
      grid: {
        left: 60,
        right: 40,
        top: 40,
        bottom: 40,
        containLabel: true,
      },
      xAxis: {
        type: "time",
        show: false,
        boundaryGap: false,
      },
      yAxis: {
        type: "value",
        show: showGrid,
        min: calculatedYRange[0],
        max: calculatedYRange[1],
        splitNumber: 5,
        axisLine: {
          show: false,
        },
        axisTick: {
          show: false,
        },
        axisLabel: {
          show: true,
          color: "rgba(18, 18, 18, 0.7)",
          fontSize: 14,
          fontFamily: "SF Pro Text, sans-serif",
          fontWeight: 500,
          formatter: (value: number) => {
            return value.toLocaleString();
          },
        },
        splitLine: {
          show: showGrid,
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
          data: chartData,
          symbol: "none",
          lineStyle: {
            color: color,
            width: 2,
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
          emphasis: {
            focus: "series",
            itemStyle: {
              color: color,
              borderColor: "white",
              borderWidth: 4,
              shadowBlur: 10,
              shadowColor: "rgba(0, 0, 0, 0.3)",
            },
          },
          animationDuration: 500,
          animationEasing: "quadraticOut",
        },
      ],
      tooltip: showTooltip
        ? {
            trigger: "axis",
            backgroundColor: "rgba(0, 0, 0, 0.7)",
            borderColor: "transparent",
            textStyle: {
              color: "#fff",
              fontSize: 12,
              fontFamily: "SF Pro Text, sans-serif",
            },
            padding: [14, 16],
            borderRadius: 12,
            formatter: (params: unknown) => {
              if (!Array.isArray(params) || params.length === 0) return "";

              const param = params[0] as { data: [string, number] };
              if (!param || !param.data) return "";

              const timestamp = param.data[0];
              const value = param.data[1];

              if (formatTooltip) {
                return formatTooltip(value, timestamp);
              }

              // 默认格式化
              const date = new Date(timestamp);
              const formatDate = date.toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
              });
              const formatTime = date.toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
                second: "2-digit",
                hour12: true,
              });

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
              type: "cross",
              crossStyle: {
                color: color,
                opacity: 0.6,
              },
              lineStyle: {
                color: color,
                opacity: 0.6,
              },
            },
          }
        : undefined,
      animation: true,
    };
  }, [
    chartData,
    color,
    gradientColors,
    showGrid,
    showTooltip,
    calculatedYRange,
    formatTooltip,
  ]);

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
    // 更新图表数据
    if (chartInstance.current) {
      chartInstance.current.setOption({
        series: [{ data: chartData }],
      });
    }
  }, [chartData]);

  return (
    <div
      ref={chartRef}
      className={cn("w-full", className)}
      style={{ width, height }}
    />
  );
}

export default Sparkline;
