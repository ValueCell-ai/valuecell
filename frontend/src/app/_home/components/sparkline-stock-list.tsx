import { MiniSparkline } from "@valuecell/charts/mini-sparkline";
import { cn, formatChange, formatPrice, getChangeType } from "@/lib/utils";
import type { StockChangeType } from "@/types/stock";

export interface SparklineStock {
  symbol: string;
  price: number;
  currency: string;
  changeAmount: number;
  changePercent: number;
  sparklineData: number[];
}

interface SparklineStockListProps extends React.HTMLAttributes<HTMLDivElement> {
  stocks: SparklineStock[];
}

interface SparklineStockItemProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "onClick"> {
  stock: SparklineStock;
}

const BASE_COLOR: Record<StockChangeType, string> = {
  positive: "#3F845F",
  negative: "#E25C5C",
  neutral: "#707070",
};

const GRADIENT_COLORS: Record<StockChangeType, [string, string]> = {
  positive: ["rgba(63, 132, 95, 0.5)", "rgba(63, 132, 95, 0)"],
  negative: ["rgba(226, 92, 92, 0.5)", "rgba(226, 92, 92, 0)"],
  neutral: ["rgba(112, 112, 112, 0.5)", "rgba(112, 112, 112, 0)"],
};

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
          className="font-semibold text-[20px] leading-[26px]"
          style={{ color: BASE_COLOR[changeType] }}
        >
          {formatPrice(stock.price, stock.currency)}
        </p>
        <div className="flex items-start gap-1">
          <span
            className="font-normal text-[12px] leading-[16px]"
            style={{ color: BASE_COLOR[changeType] }}
          >
            {formatChange(stock.changeAmount)}
          </span>
          <span
            className="font-normal text-[12px] leading-[16px]"
            style={{ color: BASE_COLOR[changeType] }}
          >
            {formatChange(stock.changePercent, "%")}
          </span>
        </div>
      </div>

      <MiniSparkline
        className="pointer-events-none"
        data={stock.sparklineData}
        color={BASE_COLOR[changeType]}
        gradientColors={GRADIENT_COLORS[changeType]}
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
