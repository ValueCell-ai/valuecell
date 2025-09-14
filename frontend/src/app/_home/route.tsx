import { Plus } from "lucide-react";
import {
  AgentRecommendList,
  AgentSuggestionsList,
  SparklineStockList,
} from "@/app/_home/components";
import { Button } from "@/components/ui/button";
import {
  StockMenu,
  StockMenuContent,
  StockMenuGroup,
  StockMenuGroupHeader,
  StockMenuHeader,
  StockMenuListItem,
} from "@/components/valuecell/menus/stock-menus";
import { agentRecommendations, agentSuggestions } from "@/mock/agent-data";
import { sparklineStockData, stockData } from "@/mock/stock-data";

function Home() {
  const handleAgentClick = (agentId: string, title: string) => {
    console.log(`Agent clicked: ${title} (${agentId})`);
  };

  return (
    <div className="flex size-full overflow-hidden">
      <main className="flex flex-1 flex-col gap-6 overflow-hidden p-8">
        <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

        <SparklineStockList stocks={sparklineStockData} />

        <AgentSuggestionsList
          title="What can I help you？"
          suggestions={agentSuggestions.map((suggestion) => ({
            ...suggestion,
            onClick: () => handleAgentClick(suggestion.id, suggestion.title),
          }))}
        />

        <AgentRecommendList
          title="Recommended Agents"
          recommendations={agentRecommendations.map((recommendation) => ({
            ...recommendation,
            onClick: () =>
              handleAgentClick(recommendation.id, recommendation.title),
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
