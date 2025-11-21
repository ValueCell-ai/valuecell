import { Link, type LinkProps } from "react-router";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn, formatChange, getChangeType } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type { StockCurrency } from "@/types/stock";

interface Stock {
  symbol: string;
  companyName: string;
  currency: StockCurrency;
  price: string;
  changePercent?: number;
  icon?: string;
  iconBgColor?: string;
}

export interface StockGroup {
  title: string;
  stocks: Stock[];
}

interface StockMenuProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface StockMenuHeaderProps
  extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

interface StockMenuGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface StockMenuGroupHeaderProps
  extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface StockIconProps extends React.HTMLAttributes<HTMLDivElement> {
  stock: Stock;
}

interface StockMenuListItemProps extends LinkProps {
  stock: Stock;
  isActive?: boolean;
}

function StockMenuHeader({
  className,
  children,
  ...props
}: StockMenuHeaderProps) {
  return (
    <h1 className={cn("px-2 font-semibold text-lg", className)} {...props}>
      {children}
    </h1>
  );
}

function StockMenu({ className, children, ...props }: StockMenuProps) {
  return (
    <div
      className={cn("flex min-h-20 flex-1 flex-col gap-6 px-5 py-6", className)}
      {...props}
    >
      {children}
    </div>
  );
}

function StockMenuGroup({
  className,
  children,
  ...props
}: StockMenuGroupProps) {
  return (
    <div
      className={cn("not-last:mb-6 flex flex-col gap-2", className)}
      {...props}
    >
      {children}
    </div>
  );
}

function StockMenuGroupHeader({
  className,
  children,
  ...props
}: StockMenuGroupHeaderProps) {
  return (
    <div className={cn("px-2 font-normal text-base", className)} {...props}>
      {children}
    </div>
  );
}

function StockIcon({ className, stock, ...props }: StockIconProps) {
  return (
    <div
      className={cn(
        "flex size-10 items-center justify-center rounded-full",
        className,
      )}
      {...props}
    >
      <Avatar className="size-full">
        <AvatarImage src={stock.icon} alt={stock.symbol} />
        <AvatarFallback className="font-medium text-muted-foreground text-xs">
          {stock.symbol.slice(0, 2)}
        </AvatarFallback>
      </Avatar>
    </div>
  );
}

function StockMenuListItem({
  className,
  stock,
  onClick,
  isActive,
  ...props
}: StockMenuListItemProps) {
  const stockColors = useStockColors();
  const changeType = getChangeType(stock.changePercent);

  return (
    <Link
      className={cn(
        "flex items-center justify-between gap-4 rounded-lg p-2",
        "cursor-pointer transition-colors hover:bg-accent/80",
        className,
        { "bg-accent/80": isActive },
      )}
      {...props}
    >
      <div className="flex flex-1 items-center gap-2.5 truncate">
        {/* icon */}
        {/* <StockIcon stock={stock} /> */}

        {/* stock info */}
        <div className="flex flex-col items-start gap-1">
          <p className="font-semibold text-foreground text-sm leading-tight">
            {stock.symbol}
          </p>
          <p className="text-muted-foreground/80 text-xs leading-none">
            {stock.companyName}
          </p>
        </div>
      </div>

      {/* price info */}
      <div className="flex flex-col items-end gap-1">
        <p className="font-semibold text-sm">{stock.price}</p>
        <p
          className="font-semibold text-xs leading-relaxed"
          style={{
            color: stockColors[changeType],
          }}
        >
          {formatChange(stock.changePercent, "%")}
        </p>
      </div>
    </Link>
  );
}

export {
  StockMenu,
  StockMenuHeader,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuListItem,
  StockIcon,
};
