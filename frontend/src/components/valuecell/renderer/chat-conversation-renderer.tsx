import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import { NavLink } from "react-router";
import { useGetAgentInfo } from "@/api/agent";
import ChatThreadArea from "@/app/agent/components/chat-conversation/chat-thread-area";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import AgentAvatar from "@/components/valuecell/agent-avatar";
import { useConversationById } from "@/store/agent-store";
import type { ChatConversationRendererProps } from "@/types/renderer";
import ScrollContainer from "../scroll/scroll-container";

const ChatConversationRenderer: FC<ChatConversationRendererProps> = ({
  content,
}) => {
  // phase => 'start' | 'end'
  const { conversation_id, agent_name, phase } = parse(content);
  const currentConversation = useConversationById(conversation_id);

  const { data: agent } = useGetAgentInfo({ agentName: agent_name });

  if (!currentConversation) return null;

  return (
    <div className="rounded-2xl border border-gray-100 bg-neutral-100 [&_#chat-item]:max-w-none">
      {/* Header section */}
      <div className="flex items-center justify-between bg-white p-4">
        <div className="flex min-w-40 items-center gap-2 rounded-full border border-gray-200 bg-gray-50 py-1 pr-5 pl-1.5">
          {agent && (
            <AgentAvatar agentName={agent.agent_name} className="size-9" />
          )}
          <p className="whitespace-nowrap font-normal text-base text-gray-950 leading-[22px]">
            {agent?.display_name || "Unknown Agent"}
          </p>
        </div>

        {phase === "start" && (
          <Button
            disabled
            className="rounded-full px-2.5 py-1.5 font-normal text-sm"
          >
            <Spinner /> Running
          </Button>
        )}

        {phase === "end" && (
          <NavLink
            to={`/agent/${agent_name}?id=${conversation_id}`}
            className="rounded-full bg-blue-500 px-2.5 py-1.5 font-normal text-sm text-white hover:bg-blue-500/80"
          >
            View
          </NavLink>
        )}
      </div>

      <ScrollContainer className="max-h-[600px]" autoScrollToBottom>
        {/* Content area */}
        <ChatThreadArea
          threads={currentConversation.threads}
          isStreaming={false}
        />
      </ScrollContainer>
    </div>
  );
};

export default memo(ChatConversationRenderer);
