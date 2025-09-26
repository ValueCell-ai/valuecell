import { useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { useGetAgentList } from "@/api/agent";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { agentSuggestions } from "@/mock/agent-data";
import { sparklineStockData } from "@/mock/stock-data";
import {
  AgentRecommendList,
  AgentSuggestionsList,
  SparklineStockList,
} from "./components";

function Home() {
  const { data: agentList } = useGetAgentList();
  const navigate = useNavigate();

  const handleAgentClick = useCallback(
    (agentId: string) => {
      navigate(`/agent/${agentId}`);
    },
    [navigate],
  );

  const recommendations = useMemo(() => {
    return agentList?.map((agent) => ({
      id: agent.agent_name,
      title: agent.agent_name,
      icon: (
        <Avatar>
          <AvatarImage src={agent.icon_url} />
          <AvatarFallback>{agent.agent_name.slice(0, 2)}</AvatarFallback>
        </Avatar>
      ),
    }));
  }, [agentList]);

  return (
    <div className="flex flex-col gap-6 p-8">
      <h1 className="font-medium text-3xl">👋 Welcome to ValueCell !</h1>

      <SparklineStockList stocks={sparklineStockData} />

      <AgentSuggestionsList
        title="What can I help you？"
        suggestions={agentSuggestions.map((suggestion) => ({
          ...suggestion,
          onClick: () => handleAgentClick(suggestion.id),
        }))}
      />

      <AgentRecommendList
        title="Recommended Agents"
        recommendations={recommendations || []}
      />
    </div>
  );
}

export default Home;
