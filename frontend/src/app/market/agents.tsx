import { useState } from "react";
import { useGetAgentList } from "@/api/agent";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { AgentMarketSkeleton } from "@/components/valuecell/skeleton";
import { AgentConfigDialog } from "../agent/dialog";
import { AgentCard } from "./components/agent-card";

export default function AgentMarket() {
  const { data: agents = [], isLoading } = useGetAgentList();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleAgentClick = (agentName: string) => {
    setSelectedAgent(agentName);
    setIsDialogOpen(true);
  };

  const handleDialogClose = (open: boolean) => {
    setIsDialogOpen(open);

    if (!open) {
      setSelectedAgent(null);
    }
  };

  if (isLoading) {
    return <AgentMarketSkeleton />;
  }

  return (
    <div className="flex size-full flex-col items-center justify-start gap-8 pt-8">
      {/* Page Title */}
      <h1 className="w-full text-center font-medium text-3xl leading-7">
        Agent Market
      </h1>

      {/* Agent Cards Grid - This is the original one */}
      {/* <ScrollContainer>
                <div className="mx-auto grid w-3/4 grid-cols-3 gap-4 space-y-4 pb-8">
                    {agents.map((agent) => (
                        <div key={agent.agent_name} className="break-inside-avoid">
                            <Link to={`/agent/${agent.agent_name}/config`}>
                                <AgentCard agent={agent} className="h-full" />
                            </Link>
                        </div>
                    ))}
                </div>
            </ScrollContainer> */}

      {/* Agent Cards Grid */}
      <ScrollContainer>
        <div className="mx-auto grid w-3/4 grid-cols-3 gap-4 space-y-4 pb-8">
          {agents.map((agent) => (
            <div key={agent.agent_name} className="break-inside-avoid">
              <div
                className="cursor-pointer"
                onClick={() => handleAgentClick(agent.agent_name)}
              >
                <AgentCard agent={agent} className="h-full" />
              </div>
            </div>
          ))}
        </div>
      </ScrollContainer>

      {/* Agent Config Dialog */}
      {selectedAgent && (
        <AgentConfigDialog
          agentName={selectedAgent}
          isOpen={isDialogOpen}
          onOpenChange={handleDialogClose}
        />
      )}
    </div>
  );
}
