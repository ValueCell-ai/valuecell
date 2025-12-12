import { useMemo, useState } from "react";
import { useGetStockHistory } from "@/api/stock";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Sparkline from "@/components/valuecell/charts/sparkline";
import { TimeUtils } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { SparklineData } from "@/types/chart";
import type { StockChangeType, StockInterval } from "@/types/stock";

interface StockHistoryChartProps {
  ticker: string;
  className?: string;
}

const INTERVALS: { label: string; value: StockInterval }[] = [
  { label: "24h", value: "1m" },
  { label: "7d", value: "1h" },
  { label: "30d", value: "1d" },
];

export const StockHistoryChart = ({
  ticker,
  className,
}: StockHistoryChartProps) => {
  const [interval, setInterval] = useState<StockInterval>("1h");

  // Calculate date range based on interval
  const { startDate, endDate } = useMemo(() => {
    const now = TimeUtils.now();

    let start = now;
    switch (interval) {
      case "1m":
        start = now.subtract(1, "day");
        break;
      case "1h":
        start = now.subtract(1, "week");
        break;
      case "1d":
        start = now.subtract(1, "month");
        break;
      default:
        start = now.subtract(1, "week");
    }

    return {
      startDate: start.utc().toISOString(),
      endDate: now.utc().toISOString(),
    };
  }, [interval]);

  const { data: historyData, isLoading } = useGetStockHistory({
    ticker,
    interval,
    start_date: startDate,
    end_date: endDate,
  });

  // Convert StockHistory[] to SparklineData format and calculate changeType
  const { sparklineData, changeType } = useMemo(() => {
    if (!historyData || historyData.length === 0) {
      return {
        sparklineData: [] as SparklineData,
        changeType: "neutral" as StockChangeType,
      };
    }

    // Convert to SparklineData format: [timestamp, price]
    const data: SparklineData = historyData.map((item) => [
      item.time,
      item.price,
    ]);

    // Determine changeType based on first and last price
    const firstPrice = historyData[0].price;
    const lastPrice = historyData[historyData.length - 1].price;

    let type: StockChangeType = "neutral";
    if (lastPrice > firstPrice) {
      type = "positive";
    } else if (lastPrice < firstPrice) {
      type = "negative";
    }

    return { sparklineData: data, changeType: type };
  }, [historyData]);

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <Tabs
        className="self-end"
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
      {isLoading ? (
        <div className="flex h-[300px] items-center justify-center">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      ) : (
        <Sparkline data={sparklineData} changeType={changeType} height={300} />
      )}
    </div>
  );
};
