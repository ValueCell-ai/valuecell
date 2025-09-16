import { Plus } from "lucide-react";
import { Outlet, useLocation } from "react-router";
import { Button } from "@/components/ui/button";
import {
  StockMenu,
  StockMenuContent,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/valuecell/menus/stock-menus";
import { stockData } from "@/mock/stock-data";

export default function HomeLayout() {
  const { pathname } = useLocation();

  // Extract stock symbol (e.g., AAPL) from path like /stock/AAPL
  const stockSymbol = pathname.split("/")[2];

  return (
    <div className="flex flex-1 overflow-hidden">
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>

      <aside className="flex h-full flex-col justify-between border-l">
        <StockMenu>
          <StockMenuHeader>My Stocks</StockMenuHeader>
          <StockMenuContent>
            {stockData.map((group) => (
              <StockMenuGroup key={group.title}>
                <StockMenuGroupHeader>{group.title}</StockMenuGroupHeader>
                {group.stocks.map((stock) => (
                  <StockMenuListItem
                    key={stock.symbol}
                    stock={stock}
                    to={`/stock/${stock.symbol}`}
                    isActive={stockSymbol === stock.symbol}
                  />
                ))}
              </StockMenuGroup>
            ))}
          </StockMenuContent>
        </StockMenu>

        <Button variant="secondary" className="mx-5 mb-6 font-bold text-sm">
          <Plus size={16} />
          Add Stocks
        </Button>
      </aside>
    </div>
  );
}
