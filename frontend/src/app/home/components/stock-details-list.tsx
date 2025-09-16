import { cn } from "@/lib/utils";

export interface StockDetailsData {
  previousClose?: string;
  dayRange?: string;
  yearRange?: string;
  marketCap?: string;
  volume?: string;
  dividendYield?: string;
}

interface StockDetailItemProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value?: string;
}

interface StockDetailsListProps extends React.HTMLAttributes<HTMLDivElement> {
  data?: StockDetailsData;
}

function StockDetailItem({
  className,
  label,
  value,
  ...props
}: StockDetailItemProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-2 text-sm",
        className,
      )}
      {...props}
    >
      <span className="text-neutral-500 tracking-tight">{label}</span>
      <span className="truncate font-bold tracking-tighter">{value}</span>
    </div>
  );
}

function StockDetailsList({
  className,
  data,
  ...props
}: StockDetailsListProps) {
  if (!data) {
    return null;
  }

  const stockItems = [
    { label: "Previous Close", value: data.previousClose },
    { label: "Day Range", value: data.dayRange },
    { label: "Year Range", value: data.yearRange },
    { label: "Market Cap", value: data.marketCap },
    { label: "Volume", value: data.volume },
    { label: "Dividend Yield", value: data.dividendYield },
  ];

  return (
    <div className={cn("flex flex-wrap gap-6 gap-x-10", className)} {...props}>
      {stockItems.map((item) => (
        <StockDetailItem
          key={item.label}
          className="min-w-[180px] flex-1"
          label={item.label}
          value={item.value}
        />
      ))}
    </div>
  );
}

export { StockDetailsList, StockDetailItem };
