import { LineChart } from "echarts/charts";
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
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
import type { MultiLineChartData } from "@/types/chart";

echarts.use([
  LineChart,
  DatasetComponent,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
]);

interface ModelMultiLineProps {
  data: MultiLineChartData;
  width?: number | string;
  height?: number | string;
  className?: string;
  showLegend?: boolean;
}

function ModelMultiLine({
  data,
  width = "100%",
  height = "100%",
  showLegend = true,
  className,
}: ModelMultiLineProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<ECharts | null>(null);

  const option: EChartsOption = useMemo(() => {
    const headers = data[0];
    const seriesCount = headers.length - 1;

    // Get the last row data (latest values)
    const lastRow = data[data.length - 1];

    // Create a map to store the latest value for each series
    const latestValues: Record<string, number> = {};
    for (let i = 1; i < headers.length; i++) {
      latestValues[headers[i]] = lastRow[i] as number;
    }

    return {
      dataset: {
        source: data,
      },
      legend: {
        show: showLegend,
        type: "scroll",
        bottom: 10,
        itemGap: 20,
        itemWidth: 14,
        itemHeight: 14,
        textStyle: {
          rich: {
            name: {
              fontSize: 14,
              fontWeight: 600,
              color: "#1f2937",
              lineHeight: 20,
            },
            value: {
              fontSize: 12,
              fontWeight: 500,
              color: "#6b7280",
              lineHeight: 18,
            },
          },
        },
        formatter: (name: string) => {
          const value = latestValues[name];
          const formattedValue =
            value?.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            }) || "N/A";

          return `{name|${name}}\n{value|$${formattedValue}}`;
        },
      },
      grid: {
        left: 0,
        right: 20,
        top: 0,
        bottom: showLegend ? 80 : 0,
      },
      xAxis: {
        type: "category",
        axisLabel: {
          formatter: (value: string) =>
            TimeUtils.formatUTC(value, TIME_FORMATS.MODAL_TRADE_TIME),
        },
      },
      yAxis: {
        type: "value",
        scale: true,
      },
      tooltip: {
        trigger: "axis",
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return "";

          const date = TimeUtils.formatUTC(
            params[0].axisValue,
            TIME_FORMATS.MODAL_TRADE_TIME,
          );

          const items = params
            .map((param) => {
              const value = param.value[param.seriesIndex + 1];
              const formattedValue =
                typeof value === "number"
                  ? `$${value.toLocaleString("en-US", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}`
                  : "N/A";

              return `${param.marker} ${param.seriesName}: <strong>${formattedValue}</strong>`;
            })
            .join("<br/>");

          return `<strong>${date}</strong><br/>${items}`;
        },
      },
      series: Array.from({ length: seriesCount }, () => ({
        type: "line",
        smooth: true,
        showSymbol: false,
        emphasis: { focus: "series" },
      })),
    };
  }, [data, showLegend]);

  useChartResize(chartInstance);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);
    chartInstance.current.setOption(option);

    return () => {
      chartInstance.current?.dispose();
    };
  }, [option]);

  return (
    <div
      ref={chartRef}
      className={cn("w-full", className)}
      style={{ width, height }}
    />
  );
}

export default ModelMultiLine;
