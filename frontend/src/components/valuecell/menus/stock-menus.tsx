import type { ScrollAreaProps } from "@radix-ui/react-scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn, formatChange, formatPrice, getChangeType } from "@/lib/utils";

interface Stock {
  symbol: string;
  companyName: string;
  price: number;
  currency: string;
  changePercent: number;
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

interface StockMenuContentProps extends ScrollAreaProps {
  children: React.ReactNode;
}

interface StockMenuGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface StockMenuGroupHeaderProps
  extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

interface StockMenuListItemProps
  extends Omit<React.HTMLAttributes<HTMLButtonElement>, "onClick"> {
  stock: Stock;
  onClick?: (stock: Stock) => void;
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

function StockMenuContent({
  className,
  children,
  ...props
}: StockMenuContentProps) {
  return (
    <ScrollArea className={cn("min-h-0 w-full", className)} {...props}>
      {children}
    </ScrollArea>
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

function StockMenuListItem({
  className,
  stock,
  onClick,
  ...props
}: StockMenuListItemProps) {
  const changeType = getChangeType(stock.changePercent);

  return (
    <button
      className={cn(
        "flex items-center justify-between gap-4 rounded-xl p-2",
        "transition-colors hover:bg-accent/80",
        className,
      )}
      onClick={() => onClick?.(stock)}
      {...props}
    >
      <div className="flex flex-1 items-center gap-2.5">
        {/* icon */}
        <div
          className="flex h-10 w-10 items-center justify-center rounded-full"
          style={{ backgroundColor: stock.iconBgColor }}
        >
          {stock.icon ? (
            <Avatar>
              <AvatarImage src={stock.icon} alt={stock.symbol} />
              <AvatarFallback className="font-medium text-xs">
                {stock.symbol.slice(0, 2)}
              </AvatarFallback>
            </Avatar>
          ) : (
            <span className="font-medium text-muted-foreground text-xs">
              {stock.symbol.slice(0, 2)}
            </span>
          )}
        </div>

        {/* stock info */}
        <div className="flex flex-col items-start gap-1">
          <p className="font-semibold text-foreground text-sm leading-tight">
            {stock.symbol}
          </p>
          <p className="truncate text-muted-foreground/80 text-xs leading-none">
            {stock.companyName}
          </p>
        </div>
      </div>

      {/* price info */}
      <div className="flex flex-col gap-1">
        <p className="font-semibold text-sm">
          {formatPrice(stock.price, stock.currency)}
        </p>
        <p
          className={cn(
            "font-semibold text-xs leading-relaxed",
            { "text-green-700": changeType === "positive" },
            { "text-red-700": changeType === "negative" },
          )}
        >
          {formatChange(stock.changePercent, "%")}
        </p>
      </div>
    </button>
  );
}

export {
  StockMenu,
  StockMenuHeader,
  StockMenuContent,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuListItem,
};
