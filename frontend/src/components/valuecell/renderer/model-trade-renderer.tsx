import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import MultiLineChart from "@/components/valuecell/charts/model-multi-line";
import type { ModelTradeRendererProps } from "@/types/renderer";

/**
 * Model Trade Renderer
 *
 * Renders a multi-line chart using ECharts with dataset format.
 * Accepts JSON string from backend and parses it.
 *
 * @example
 * ```tsx
 * const content = JSON.stringify({
 *   title: "Portfolio Value History",
 *   data: [
 *     ['Time', 'Model 1', 'Model 2'],
 *     ['2024-01', 120, 200],
 *     ['2024-02', 132, 154],
 *   ],
 *   create_time: "2025-10-21 02:57:22"
 * });
 *
 * <ModelTradeRenderer content={content} height={400} />
 * ```
 */
const ModelTradeRenderer: FC<ModelTradeRendererProps> = ({ content }) => {
  const { title, data } = parse(content);
  const parsedData = parse(data);

  return (
    <div className="flex size-full flex-col justify-between gap-3 px-2 py-6">
      <div className="flex flex-1 flex-col gap-6">
        <h3 className="font-semibold text-base text-gray-950">{title}</h3>
        <MultiLineChart data={parsedData} height={"90%"} />
      </div>

      <div className="flex w-full flex-col gap-4">
        <p className="font-medium text-gray-950 text-sm">
          Disclaimer & Tool Reminder:
        </p>
        <div className="flex w-full flex-col gap-2 text-gray-700 text-xs">
          <p className="w-full">
            1. The AI tools are for simulation only and do not provide
            investment advice
          </p>
          <p className="w-full">
            2. The tools may contain errors or delays and cannot account for all
            market factors. You are solely responsible for your trading
            decisions. Use caution — markets involve risk.
          </p>
        </div>
      </div>
    </div>
  );
};

export default memo(ModelTradeRenderer);
