import { ArrowRight } from "lucide-react";
import { Link, useParams } from "react-router";
import BackButton from "@/components/valuecell/button/back-button";
import PreviewMarkdown from "@/components/valuecell/markdown/preview-markdown";
import ScrollContainer from "@/components/valuecell/scroll-container";
import { agentData } from "@/mock/agent-data";

export default function AgentConfig() {
  const { agentId } = useParams();

  const agent = agentData[agentId as keyof typeof agentData];

  return (
    <div className="flex flex-1 flex-col gap-8 overflow-hidden py-8">
      <BackButton className="mx-8" />

      {/* Agent info and configure button */}
      <div className="mb-10 flex items-start justify-between px-8">
        <div className="flex flex-col gap-4">
          {agent.avatar}
          <div className="flex flex-col gap-2">
            <h1 className="font-semibold text-4xl leading-9">{agent.name}</h1>
            <p className="text-base text-neutral-500 leading-6">
              {agent.description}
            </p>
          </div>
        </div>

        <Link
          className="flex items-center gap-2 rounded-md bg-black px-5 py-3 font-semibold text-base text-white hover:bg-black/80"
          to={`/agent/${agentId}`}
        >
          Activate Chat
          <ArrowRight size={16} />
        </Link>
      </div>

      <ScrollContainer className="px-8">
        <PreviewMarkdown content={agent.content} />
      </ScrollContainer>
    </div>
  );
}
