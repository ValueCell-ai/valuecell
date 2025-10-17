import { Link } from "react-router";
import { useGetAgentList } from "@/api/agent";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { AgentMarketSkeleton } from "@/components/valuecell/skeleton";
import { AgentCard } from "./components/agent-card";

export default function AgentMarket() {
  const { data: agents = [], isLoading } = useGetAgentList();

  if (isLoading) {
    return <AgentMarketSkeleton />;
  }

  return (
    <div className="flex size-full flex-col items-center justify-start gap-8 pt-8">
      {/* Page Title */}
      <h1 className="w-full text-center font-medium text-3xl leading-7">
        Agent Market
      </h1>

      {/* Agent Cards Grid */}
      <ScrollContainer>
        <div className="mx-auto w-3/4 columns-3 gap-4 space-y-4 pb-8">
          {agents.map((agent) => (
            <div key={agent.agent_name} className="break-inside-avoid">
              <Link to={`/agent/${agent.agent_name}/config`}>
                <AgentCard agent={agent} />
              </Link>
            </div>
          ))}
        </div>
      </ScrollContainer>
    </div>
  );
}
