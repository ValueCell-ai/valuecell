import MiniSparkline from "@valuecell/charts/mini-sparkline";
import { memo } from "react";
import { SparklineStockListSkeleton } from "@/components/valuecell/skeleton";
import { cn, formatChange, getChangeType, numberFixed } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type { SparklineData } from "@/types/chart";
import type { StockCurrency } from "@/types/stock";

export interface SparklineStock {
  symbol: string; // Stock symbol (e.g., "NASDAQ", "HSI", "SSE")
  price: number;
  currency: StockCurrency;
  changeAmount: number;
  changePercent?: number;
  sparklineData: SparklineData;
}

interface SparklineStockListProps extends React.HTMLAttributes<HTMLDivElement> {
  stocks: SparklineStock[];
}

interface SparklineStockItemProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "onClick"> {
  stock: SparklineStock;
}

function SparklineStockItem({
  className,
  stock,
  ...props
}: SparklineStockItemProps) {
  const stockColors = useStockColors();
  const changeType = getChangeType(stock.changePercent);

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 rounded-lg border border-gray-100 bg-white px-4 py-3",
        className,
      )}
      {...props}
    >
      <div className="flex flex-col items-start gap-1 font-semibold">
        <p className="text-gray-400 text-sm">{stock.symbol}</p>
        <p
          className="text-xl"
          style={{
            color: stockColors[changeType],
          }}
        >
          {numberFixed(stock.price, 2)}
        </p>
        <div
          className="flex gap-1 font-normal text-xs"
          style={{
            color: stockColors[changeType],
          }}
        >
          <span>{formatChange(stock.changeAmount)}</span>
          <span>{formatChange(stock.changePercent, "%")}</span>
        </div>
      </div>

      <MiniSparkline
        className="pointer-events-none"
        data={stock.sparklineData}
        changeType={changeType}
        width={140}
        height={64}
      />
    </div>
  );
}

function SparklineStockList({
  className,
  stocks,
  ...props
}: SparklineStockListProps) {
  // Show skeleton when loading or when stocks is undefined/empty
  if (stocks.length === 0) {
    return (
      <SparklineStockListSkeleton className={className} count={3} {...props} />
    );
  }

  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3",
        className,
      )}
      {...props}
    >
      {stocks.map((stock) => (
        <SparklineStockItem key={stock.symbol} stock={stock} />
      ))}
    </div>
  );
}

export default memo(SparklineStockList);
