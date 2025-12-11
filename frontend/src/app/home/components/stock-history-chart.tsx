import { useMemo, useState } from "react";
import { useGetStockHistory } from "@/api/stock";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import CandlestickChart from "@/components/valuecell/charts/candlestick-chart";
import { TimeUtils } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { StockInterval } from "@/types/stock";

interface StockHistoryChartProps {
  ticker: string;
  className?: string;
}

const INTERVALS: { label: string; value: StockInterval }[] = [
  { label: "1H", value: "1h" },
  { label: "1D", value: "1d" },
  { label: "1W", value: "1w" },
];

export const StockHistoryChart = ({
  ticker,
  className,
}: StockHistoryChartProps) => {
  const [interval, setInterval] = useState<StockInterval>("1d");

  // Calculate date range based on interval
  const { startDate, endDate } = useMemo(() => {
    const now = TimeUtils.now();

    let start = now;
    switch (interval) {
      case "1h":
        start = now.subtract(6, "month");
        break;
      case "1d":
        start = now.subtract(3, "year");
        break;
      case "1w":
        start = now.subtract(10, "year");
        break;
      default:
        start = now.subtract(3, "year");
    }

    return {
      startDate: start.format("YYYY-MM-DD"),
      endDate: now.format("YYYY-MM-DD"),
    };
  }, [interval]);

  const { data: historyData, isLoading } = useGetStockHistory({
    ticker,
    interval,
    start_date: startDate,
    end_date: endDate,
  });

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <Tabs
        value={interval}
        onValueChange={(value) => setInterval(value as StockInterval)}
      >
        <TabsList>
          {INTERVALS.map((item) => (
            <TabsTrigger key={item.value} value={item.value}>
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <CandlestickChart
        data={historyData ?? []}
        height={500}
        loading={isLoading}
        showVolume
      />
    </div>
  );
};
