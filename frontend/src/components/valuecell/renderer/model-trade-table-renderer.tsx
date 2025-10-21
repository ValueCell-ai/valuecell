import { parse } from "best-effort-json-parser";
import { Filter } from "lucide-react";
import { type FC, memo, useMemo, useState } from "react";
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

interface GroupedData {
  table_title: string;
  items: TradeTableData[];
  allFilters: string[];
}

/**
 * Model Trade Table Renderer
 *
 * Displays trading information with tab headers and filters.
 * Renders markdown content for completed trades, positions, and instance details.
 *
 * Supports both single object and array of objects as content:
 * - Single object: Will be displayed as a single tab
 * - Array of objects: Will be grouped by `table_title` and displayed as multiple tabs
 *
 * The component groups data by `table_title` and provides filtering capability
 * for each tab based on the model filters in that group.
 *
 * @example
 * ```tsx
 * // Single object (backward compatible)
 * const singleData = JSON.stringify({
 *   title: "Trading Instance",
 *   data: `## Instance Summary...`,
 *   filters: ["deepseek/deepseek-v3.1-terminus"],
 *   table_title: "Instance Details",
 *   create_time: "2025-10-21 02:51:03"
 * });
 *
 * // Array of objects (new format)
 * const arrayData = JSON.stringify([
 *   {
 *     title: "Completed Trade 1",
 *     data: `## 🤖 GPT 5 completed...`,
 *     filters: ["openai/gpt-5"],
 *     table_title: "Completed Trades",
 *     create_time: "2025-10-21 12:50:00"
 *   },
 *   {
 *     title: "Completed Trade 2",
 *     data: `## ☀️ Claude Sonnet 4.5...`,
 *     filters: ["anthropic/claude-sonnet-4.5"],
 *     table_title: "Completed Trades",
 *     create_time: "2025-10-21 12:51:00"
 *   },
 *   {
 *     title: "Position 1",
 *     data: `## Current Positions...`,
 *     filters: ["google/gemini-2.5-pro"],
 *     table_title: "Open Positions",
 *     create_time: "2025-10-21 12:52:00"
 *   }
 * ]);
 *
 * <ModelTradeTableRenderer content={singleData} />
 * <ModelTradeTableRenderer content={arrayData} />
 * ```
 */
const ModelTradeTableRenderer: FC<ModelTradeTableRendererProps> = ({
  content,
}) => {
  // Parse content - supports both single object and array
  const parsedData: TradeTableData | TradeTableData[] = parse(content);
  const dataArray: TradeTableData[] = Array.isArray(parsedData)
    ? parsedData
    : [parsedData];

  // Group data by table_title and collect all filters for each group
  const groupedData: GroupedData[] = useMemo(() => {
    const groups = new Map<string, TradeTableData[]>();

    // Group items by table_title
    for (const item of dataArray) {
      const existing = groups.get(item.table_title) || [];
      existing.push(item);
      groups.set(item.table_title, existing);
    }

    // Convert to array and collect all unique filters for each group
    return Array.from(groups.entries()).map(([table_title, items]) => {
      const allFiltersSet = new Set<string>();
      for (const item of items) {
        for (const filter of item.filters) {
          allFiltersSet.add(filter);
        }
      }
      return {
        table_title,
        items,
        allFilters: Array.from(allFiltersSet),
      };
    });
  }, [dataArray]);

  // State for active tab and filters for each tab
  const [activeTab, setActiveTab] = useState(groupedData[0]?.table_title || "");
  const [filtersByTab, setFiltersByTab] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      groupedData.map((group) => [group.table_title, "ALL MODELS"]),
    ),
  );

  // Helper function to get filtered items for a specific group and filter
  const getFilteredItems = (group: GroupedData, filter: string) => {
    if (filter === "ALL MODELS") return group.items;
    return group.items.filter((item) => item.filters.includes(filter));
  };

  if (groupedData.length === 0) {
    return <div className="p-4 text-muted-foreground">No data available</div>;
  }

  return (
    <Tabs
      value={activeTab}
      onValueChange={setActiveTab}
      className="size-full flex-col py-4"
    >
      {/* Tab Navigation */}
      <ScrollContainer className="pb-3">
        <TabsList>
          {groupedData.map((group) => (
            <TabsTrigger
              className="cursor-pointer"
              key={group.table_title}
              value={group.table_title}
            >
              {group.table_title}
            </TabsTrigger>
          ))}
        </TabsList>
      </ScrollContainer>

      {groupedData.map((group) => {
        const currentFilter = filtersByTab[group.table_title] || "ALL MODELS";
        const filterOptions = ["ALL MODELS", ...group.allFilters];
        const filteredItems = getFilteredItems(group, currentFilter).reverse();

        return (
          <TabsContent
            key={group.table_title}
            value={group.table_title}
            className="h-full"
          >
            {/* Filter Bar */}
            <div className="flex items-center gap-2 border-border border-b px-4 py-2.5 text-muted-foreground text-xs">
              <Filter className="size-3.5" />
              <span className="font-medium">Filter:</span>
              <Select
                value={currentFilter}
                onValueChange={(value) => {
                  setFiltersByTab((prev) => ({
                    ...prev,
                    [group.table_title]: value,
                  }));
                }}
              >
                <SelectTrigger size="sm" className="h-8 w-fit min-w-[140px]">
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent align="end">
                  {filterOptions.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Content Area */}
            <ScrollContainer className="p-3">
              {filteredItems.length > 0 ? (
                <div className="flex flex-col gap-4">
                  {filteredItems.map((item, index) => (
                    <div
                      key={`${item.title}-${index}`}
                      className="rounded-lg border border-border bg-gray-50 p-4"
                    >
                      <ScrollContainer>
                        <MarkdownRenderer content={item.data} />
                      </ScrollContainer>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-muted-foreground text-sm">
                  No data available for selected filter
                </div>
              )}
            </ScrollContainer>

            {/* Footer */}
            <div className="border-border border-t px-3 py-2 text-right text-muted-foreground text-xs">
              Last updated: {TimeUtils.nowUTC().format(TIME_FORMATS.DATE)}
            </div>
          </TabsContent>
        );
      })}
    </Tabs>
  );
};

export default memo(ModelTradeTableRenderer);
