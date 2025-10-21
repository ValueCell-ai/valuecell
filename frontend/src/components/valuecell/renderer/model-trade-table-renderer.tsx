import { parse } from "best-effort-json-parser";
import { type FC, memo, useState } from "react";
import type { ModelTradeTableRendererProps } from "@/types/renderer";
import MarkdownRenderer from "./markdown-renderer";

interface TradeTableData {
  title: string;
  data: string; // Markdown content
  filters: string[];
  table_title: string;
  create_time: string;
}

/**
 * Model Trade Table Renderer
 *
 * Displays trading information with tab header and filters.
 * Renders markdown content for completed trades, positions, and instance details.
 *
 * The component uses `table_title` as the tab label. The `data` field contains
 * markdown-formatted content that will be rendered in the main content area.
 *
 * @example
 * ```tsx
 * // Instance details with summary tables
 * const instanceData = JSON.stringify({
 *   title: "Trading Instance: trade_20251021_104538_59d5aa9b",
 *   data: `## Instance Summary\n\n| Metric | Value |\n|---|---|\n| Total P&L | $-3,961.30 |`,
 *   filters: ["deepseek/deepseek-v3.1-terminus"],
 *   table_title: "Instance Details",
 *   create_time: "2025-10-21 02:51:03"
 * });
 *
 * // Completed trades view
 * const tradesData = JSON.stringify({
 *   title: "Completed Trades - All Models",
 *   data: `## 🤖 GPT 5 completed a **long** trade...\n**NET P&L:** -$177.44`,
 *   filters: ["openai/gpt-5", "anthropic/claude-sonnet-4.5"],
 *   table_title: "Completed Trades",
 *   create_time: "2025-10-21 12:50:00"
 * });
 *
 * <ModelTradeTableRenderer content={instanceData} />
 * <ModelTradeTableRenderer content={tradesData} />
 * ```
 */
const ModelTradeTableRenderer: FC<ModelTradeTableRendererProps> = ({
  content,
}) => {
  const { data, filters, table_title }: TradeTableData = parse(content);

  const [selectedFilter, setSelectedFilter] = useState("ALL MODELS");

  // Get all available models from filters
  const modelOptions = ["ALL MODELS", ...(filters || [])];

  return (
    <div className="flex size-full flex-col bg-gray-50">
      {/* Tab Navigation */}
      <div className="flex items-center border-gray-300 border-b bg-white">
        <button
          type="button"
          className="border-gray-800 border-b-2 bg-gray-100 px-4 py-2 font-medium text-gray-900 text-xs"
        >
          {table_title}
        </button>
      </div>

      {/* Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Filter Bar */}
        <div className="flex items-center justify-between border-gray-200 border-b bg-white px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="font-medium text-gray-700 text-xs">FILTER:</span>
            <select
              value={selectedFilter}
              onChange={(e) => setSelectedFilter(e.target.value)}
              className="rounded border border-gray-300 bg-white px-3 py-1.5 font-medium text-gray-900 text-xs transition-colors hover:border-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              {modelOptions.map((option) => (
                <option key={option} value={option}>
                  {option.toUpperCase()} ▼
                </option>
              ))}
            </select>
          </div>
          <div className="text-gray-600 text-xs">
            {table_title && `Showing ${table_title}`}
          </div>
        </div>

        {/* Trade List/Content */}
        <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
          <div className="mx-auto max-w-5xl">
            <MarkdownRenderer content={data} />
          </div>
        </div>

        {/* Footer */}
        <div className="border-gray-200 border-t bg-gray-50 px-4 py-2 text-right text-gray-500 text-xs">
          Last updated: {new Date().toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default memo(ModelTradeTableRenderer);
