import { ArrowRight } from "lucide-react";
import { Link, Navigate, useParams } from "react-router";
import { useGetAgentInfo } from "@/api/agent";
import BackButton from "@/components/valuecell/button/back-button";
import PreviewMarkdown from "@/components/valuecell/markdown/preview-markdown";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import type { Route } from "./+types/config";

export default function AgentConfig() {
  const { agentName } = useParams<Route.LoaderArgs["params"]>();
  const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });

  if (!agentName && !isLoadingAgent) return <Navigate to="/" replace />;

  return (
    <div className="flex flex-1 flex-col gap-8 overflow-hidden py-8">
      <BackButton className="mx-8" />

      {/* Agent info and configure button */}
      <div className="mb-10 flex items-start justify-between px-8">
        <div className="flex flex-col gap-4">
          {agent?.icon_url}
          <div className="flex flex-col gap-2">
            <h1 className="font-semibold text-4xl leading-9">
              {agent?.agent_name}
            </h1>
            {/* <p className="text-base text-neutral-500 leading-6">
              {agent?.description}
            </p> */}
          </div>
        </div>

        <Link
          className="flex items-center gap-2 rounded-md bg-black px-5 py-3 font-semibold text-base text-white hover:bg-black/80"
          to={`/agent/${agentName}`}
        >
          Activate Chat
          <ArrowRight size={16} />
        </Link>
      </div>

      <ScrollContainer className="px-8">
        <PreviewMarkdown content={agent?.description ?? ""} />
      </ScrollContainer>
    </div>
  );
}
