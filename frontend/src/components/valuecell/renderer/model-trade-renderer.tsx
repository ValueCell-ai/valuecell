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
    <div className="flex size-full flex-col justify-center gap-3">
      <h3 className="font-medium text-base text-gray-900 leading-tight">
        {title}
      </h3>
      <MultiLineChart data={parsedData} height={"80%"} />
    </div>
  );
};

export default memo(ModelTradeRenderer);
