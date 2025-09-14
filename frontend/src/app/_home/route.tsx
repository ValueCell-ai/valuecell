import { Plus } from "lucide-react";
import { AgentSuggestionsList } from "@/app/_home/components/agent-suggestions-list";
import { SparklineStockList } from "@/app/_home/components/sparkline-stock-list";
import {
  StockMenu,
  StockMenuContent,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/menus/stock-menus";
import { Button } from "@/components/ui/button";
import { agentSuggestions } from "@/mock/agent-data";
import { sparklineStockData, stockData } from "@/mock/stock-data";

function Home() {
  const handleAgentClick = (agentId: string, title: string) => {
    console.log(`Agent clicked: ${title} (${agentId})`);
  };

  return (
    <div className="flex size-full">
      <main className="flex flex-1 flex-col gap-6 p-8">
        <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

        <SparklineStockList stocks={sparklineStockData} />

        <AgentSuggestionsList
          title="What can I help you？"
          suggestions={agentSuggestions.map((suggestion) => ({
            ...suggestion,
            onClick: () => handleAgentClick(suggestion.id, suggestion.title),
          }))}
        />
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
