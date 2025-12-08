import { ArrowRight } from "lucide-react";
import { Link, Navigate, useParams } from "react-router";
import { useEnableAgent, useGetAgentInfo } from "@/api/agent";
import { Button } from "@/components/ui/button";
import BackButton from "@/components/valuecell/button/back-button";
import AgentAvatar from "@/components/valuecell/icon/agent-avatar";
import { MarkdownRenderer } from "@/components/valuecell/renderer";
import type { Route } from "./+types/config";

export default function AgentConfig() {
  const { agentName } = useParams<Route.LoaderArgs["params"]>();
  const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });
  const { mutateAsync } = useEnableAgent();

  if (!agentName && !isLoadingAgent) return <Navigate to="/" replace />;

  const handleEnableAgent = async () => {
    await mutateAsync({
      agentName: agentName ?? "",
      enabled: !agent?.enabled,
    });
  };

  return (
    <div className="scroll-container flex flex-1 flex-col gap-4 p-8">
      <BackButton />

      {/* Agent info and configure button */}
      <div className="mb-6 flex items-center justify-between rounded-lg bg-gray-50 px-4 py-8">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <AgentAvatar agentName={agentName ?? ""} className="size-16" />
            <h1 className="font-semibold text-4xl leading-9">
              {agent?.display_name}
            </h1>
          </div>
          <div className="flex gap-2">
            {agent?.agent_metadata.tags.map((tag) => (
              <span
                key={tag}
                className="text-nowrap rounded-md border border-gray-200 px-3 py-1 font-normal text-gray-700 text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {agent?.enabled ? (
          <div className="flex items-center gap-4">
            {agentName !== "ValueCellAgent" && (
              <Button variant="secondary" onClick={handleEnableAgent}>
                Disable
              </Button>
            )}
            <Link
              className="flex items-center gap-2 rounded-md bg-black px-5 py-1.5 font-semibold text-base text-white hover:bg-black/80"
              to={`/agent/${agentName}`}
            >
              Chat <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <Link
            className="flex items-center gap-2 rounded-md bg-black px-5 py-3 font-semibold text-base text-white hover:bg-black/80"
            to={`/agent/${agentName}`}
            onClick={handleEnableAgent}
          >
            Collect and chat
            <ArrowRight size={16} />
          </Link>
        )}
      </div>

      <MarkdownRenderer content={agent?.description ?? ""} />
    </div>
  );
}
