import { Plus } from "lucide-react";
import {
  StockMenu,
  StockMenuContent,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/menus/stock-menus";
import { Button } from "@/components/ui/button";
import { stockData } from "@/mock/stock-data";

function Home() {
  return (
    <div className="flex size-full">
      <main className="flex-1"></main>

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
