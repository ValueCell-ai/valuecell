import { Plus } from "lucide-react";
import { SparklineStockList } from "@/components/menus/sparkline-stock-menus";
import {
  StockMenu,
  StockMenuContent,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/menus/stock-menus";
import { Button } from "@/components/ui/button";
import { sparklineStockData, stockData } from "@/mock/stock-data";

function Home() {
  return (
    <div className="flex size-full">
      <main className="flex flex-1 flex-col gap-6 p-8">
        <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

        <SparklineStockList stocks={sparklineStockData} />
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
                    onClick={() => {
                      console.log("Selected stock:", stock.symbol);
                    }}
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

export default Home;
