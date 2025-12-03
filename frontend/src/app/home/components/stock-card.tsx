import { AgentMenuCard } from "@/components/valuecell/menus/agent-menus";
import { StockChart } from "./stock-chart";

export function StockCard({ ticker }: { ticker: string }) {
  const interval: StockInterval = "1d";
  const endDate = useMemo(() => new Date().toISOString().split("T")[0], []);
  const startDate = useMemo(
    () => new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
    [],
  );

  const { data: stockHistory, isLoading } = useGetStockHistory({
    ticker,
    interval,
    start_date: startDate,
    end_date: endDate,
  });

  const { data: stockPrice } = useGetStockPrice({ ticker });

  const hasData = !!stockHistory?.prices && stockHistory.prices.length > 0;
  if (!isLoading && !hasData) return null;

  return (
    <AgentMenuCard className="flex h-60 w-full flex-col overflow-hidden p-0">
      <div className="relative min-h-[180px] w-full flex-1 p-2">
        <StockChart
          ticker={ticker}
          title={ticker}
          axisVisible={false}
          valueLabel={
            stockPrice?.price_formatted ||
            (hasData
              ? String(
                  stockHistory!.prices[stockHistory!.prices.length - 1]
                    .close_price,
                )
              : undefined)
          }
        />
      </div>
    </AgentMenuCard>
  );
}
import { useMemo } from "react";
import { useGetStockHistory, useGetStockPrice } from "@/api/stock";
import type { StockInterval } from "@/types/stock";
