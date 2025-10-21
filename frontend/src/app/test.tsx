import ModelTradeRenderer from "@/components/valuecell/renderer/model-trade-renderer";
import ModelTradeTableRenderer from "@/components/valuecell/renderer/model-trade-table-renderer";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import {
  mockCompletedTradesData,
  mockModelTradeData,
  mockModelTradeDataMultiple,
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

        {/* Trade Table - Completed Trades */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="h-[600px]">
            <ModelTradeTableRenderer content={mockCompletedTradesData} />
          </div>
        </div>

        {/* Trade Table - Instance Details */}
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <div className="h-[600px]">
            <ModelTradeTableRenderer content={mockModelTradeTableData} />
          </div>
        </div>

        {/* Single Model Chart */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="h-96">
            <ModelTradeRenderer content={mockModelTradeData} />
          </div>
        </div>

        {/* Multiple Models Chart */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="h-96">
            <ModelTradeRenderer content={mockModelTradeDataMultiple} />
          </div>
        </div>
      </div>
    </ScrollContainer>
  );
}
