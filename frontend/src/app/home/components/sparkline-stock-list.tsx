import MiniSparkline from "@valuecell/charts/mini-sparkline";
import { STOCK_COLORS } from "@/constants/stock";
import { cn, formatChange, formatPrice, getChangeType } from "@/lib/utils";
import type { SparklineData } from "@/types/chart";

export interface SparklineStock {
  symbol: string;
  price: number;
  currency: string;
  changeAmount: number;
  changePercent: number;
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
  const changeType = getChangeType(stock.changePercent);

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 rounded-md border border-[#eef0f3] p-3",
        className,
      )}
      {...props}
    >
      <div className="flex flex-col items-start gap-1">
        <div className="flex items-center gap-1">
          <p className="font-semibold text-[#707070] text-[14px] leading-[20px]">
            {stock.symbol}
          </p>
        </div>
        <p
          className={`font-semibold text-[20px] leading-[26px]`}
          style={{
            color: STOCK_COLORS[changeType],
          }}
        >
          {formatPrice(stock.price, stock.currency)}
        </p>
        <div className="flex items-start gap-1">
          <span
            className={`font-normal text-[12px] leading-[16px]`}
            style={{
              color: STOCK_COLORS[changeType],
            }}
          >
            {formatChange(stock.changeAmount)}
          </span>
          <span
            className={`font-normal text-[12px] leading-[16px]`}
            style={{
              color: STOCK_COLORS[changeType],
            }}
          >
            {formatChange(stock.changePercent, "%")}
          </span>
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
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
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

export { SparklineStockList, SparklineStockItem };
