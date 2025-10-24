import AppConversationSheet from "@/components/valuecell/app-conversation-sheet";
import ModelTradeRenderer from "@/components/valuecell/renderer/model-trade-renderer";
import ModelTradeTableRenderer from "@/components/valuecell/renderer/model-trade-table-renderer";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import {
  mockCompletedTradesData,
  mockModelTradeData,
  mockModelTradeDataMultiple,
  mockModelTradeTableArrayData,
  mockModelTradeTableData,
} from "@/mock/model-trade-data";

export default function Test() {
  return (
    <ScrollContainer className="size-full">
      <div className="flex min-h-screen flex-col gap-8 p-8">
        <div className="flex flex-col gap-2">
          <h1 className="font-bold text-2xl text-gray-900">
            Model Trade Renderer Test
          </h1>
          <p className="text-gray-600 text-sm">
            Custom legend cards with portfolio value visualization and trading
            tables
          </p>
        </div>

        {/* Conversation Sheet Demo */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="px-4 py-6">
            <h2 className="mb-2 font-semibold text-gray-900 text-lg">
              Conversation History Sheet
            </h2>
            <p className="mb-4 text-gray-500 text-xs">
              Click the button to open the conversation history sheet with
              shadcn sidebar components
            </p>
            <AppConversationSheet />
          </div>
        </div>

        {/* Trade Table - Array Format (NEW: Multiple Tabs with Filtering) */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="mb-2 px-4 pt-4">
            <h2 className="font-semibold text-gray-900 text-lg">
              Array Format - Multiple Tabs
            </h2>
            <p className="text-gray-500 text-xs">
              Demonstrates tab grouping by table_title and per-tab filtering
            </p>
          </div>
          <div className="h-[600px]">
            <ModelTradeTableRenderer content={mockModelTradeTableArrayData} />
          </div>
        </div>

        {/* Trade Table - Completed Trades (Single Object) */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="mb-2 px-4 pt-4">
            <h2 className="font-semibold text-gray-900 text-lg">
              Single Object - Completed Trades
            </h2>
            <p className="text-gray-500 text-xs">
              Backward compatible single object format
            </p>
          </div>
          <div className="h-[600px]">
            <ModelTradeTableRenderer content={mockCompletedTradesData} />
          </div>
        </div>

        {/* Trade Table - Instance Details (Single Object) */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="mb-2 px-4 pt-4">
            <h2 className="font-semibold text-gray-900 text-lg">
              Single Object - Instance Details
            </h2>
            <p className="text-gray-500 text-xs">
              Instance summary and positions
            </p>
          </div>
          <div className="h-[600px]">
            <ModelTradeTableRenderer content={mockModelTradeTableData} />
          </div>
        </div>

        {/* Single Model Chart */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-2">
            <h2 className="font-semibold text-gray-900 text-lg">
              Single Model Chart
            </h2>
            <p className="text-gray-500 text-xs">Portfolio value over time</p>
          </div>
          <div className="h-96">
            <ModelTradeRenderer content={mockModelTradeData} />
          </div>
        </div>

        {/* Multiple Models Chart */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-2">
            <h2 className="font-semibold text-gray-900 text-lg">
              Multiple Models Chart
            </h2>
            <p className="text-gray-500 text-xs">
              Comparing multiple models performance
            </p>
          </div>
          <div className="h-96">
            <ModelTradeRenderer content={mockModelTradeDataMultiple} />
          </div>
        </div>
      </div>
    </ScrollContainer>
  );
}
