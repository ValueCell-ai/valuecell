import { parse } from "best-effort-json-parser";
import { Filter } from "lucide-react";
import { type FC, memo, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import type { ModelTradeTableRendererProps } from "@/types/renderer";
import ScrollContainer from "../scroll/scroll-container";
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
  const modelOptions = ["ALL MODELS", ...filters];

  return (
    <Tabs value={table_title} className="flex size-full flex-col">
      {/* Tab Navigation */}
      <TabsList className="bg-transparent px-3">
        <TabsTrigger value={table_title}>{table_title}</TabsTrigger>
      </TabsList>

      {/* Filter Bar */}
      <div className="flex items-center gap-2 border-border border-b px-4 py-2.5 text-muted-foreground text-xs">
        <Filter className="size-3.5" />
        <span className="font-medium">Filter:</span>
        <Select value={selectedFilter} onValueChange={setSelectedFilter}>
          <SelectTrigger size="sm" className="h-8 w-fit min-w-[140px]">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent align="end">
            {modelOptions.map((option) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Content Area */}
      <TabsContent
        value={table_title}
        className="m-0 flex flex-1 flex-col overflow-hidden"
      >
        {/* Trade List/Content */}
        <ScrollContainer className="p-3">
          <MarkdownRenderer content={data} />
        </ScrollContainer>

        {/* Footer */}
        <div className="border-border border-t px-3 py-2 text-right text-muted-foreground text-xs">
          Last updated: {TimeUtils.nowUTC().format(TIME_FORMATS.DATE)}
        </div>
      </TabsContent>
    </Tabs>
  );
};

export default memo(ModelTradeTableRenderer);
