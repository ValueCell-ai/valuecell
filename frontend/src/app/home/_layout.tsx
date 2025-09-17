import { Plus } from "lucide-react";
import { Outlet, useLocation } from "react-router";
import { Button } from "@/components/ui/button";
import {
  StockMenu,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/valuecell/menus/stock-menus";
import ScrollContainer from "@/components/valuecell/scroll-container";
import { stockData } from "@/mock/stock-data";

export default function HomeLayout() {
  const { pathname } = useLocation();

  // Extract stock symbol (e.g., AAPL) from path like /stock/AAPL
  const stockSymbol = pathname.split("/")[2];

  return (
    <div className="flex flex-1 overflow-hidden">
      <ScrollContainer className="flex-1">
        <Outlet />
      </ScrollContainer>

      <aside className="flex h-full flex-col justify-between border-l">
        <StockMenu>
          <StockMenuHeader>My Stocks</StockMenuHeader>
          <ScrollContainer>
            {stockData.map((group) => (
              <StockMenuGroup key={group.title}>
                <StockMenuGroupHeader>{group.title}</StockMenuGroupHeader>
                {group.stocks.map((stock) => (
                  <StockMenuListItem
                    key={stock.symbol}
                    stock={stock}
                    to={`/stock/${stock.symbol}`}
                    isActive={stockSymbol === stock.symbol}
                    replace={!!stockSymbol}
                  />
                ))}
              </StockMenuGroup>
            ))}
          </ScrollContainer>
        </StockMenu>

        <Button variant="secondary" className="mx-5 mb-6 font-bold text-sm">
          <Plus size={16} />
          Add Stocks
        </Button>
      </aside>
    </div>
  );
}
