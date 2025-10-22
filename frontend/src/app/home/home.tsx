import { useCallback } from "react";
import { useNavigate } from "react-router";
import { HOME_STOCK_SHOW } from "@/constants/stock";
import { agentSuggestions } from "@/mock/agent-data";
import { AgentSuggestionsList, SparklineStockList } from "./components";
import { useSparklineStocks } from "./hooks/use-sparkline-stocks";

function Home() {
  const navigate = useNavigate();

  const handleAgentClick = useCallback(
    (agentId: string) => {
      navigate(`/agent/${agentId}`);
    },
    [navigate],
  );

  const { sparklineStocks } = useSparklineStocks(HOME_STOCK_SHOW);

  return (
    <div className="flex flex-col gap-6 p-8">
      <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

      <SparklineStockList stocks={sparklineStocks} />

      <AgentSuggestionsList
        title="What can I help you？"
        suggestions={agentSuggestions.map((suggestion) => ({
          ...suggestion,
          onClick: () => handleAgentClick(suggestion.id),
        }))}
      />
    </div>
  );
}

export default Home;
