import { agentRecommendations, agentSuggestions } from "@/mock/agent-data";
import { sparklineStockData } from "@/mock/stock-data";
import {
  AgentRecommendList,
  AgentSuggestionsList,
  SparklineStockList,
} from "./components";

function Home() {
  const handleAgentClick = (agentId: string, title: string) => {
    console.log(`Agent clicked: ${title} (${agentId})`);
  };

  return (
    <div className="flex flex-col gap-6 p-8">
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
    </div>
  );
}

export default Home;
