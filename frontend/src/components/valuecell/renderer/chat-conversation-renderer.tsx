import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import ChatThreadArea from "@/app/agent/components/chat-conversation/chat-thread-area";
import { useAgentStore } from "@/provider/agent-store-provider";
import type { ChatConversationRendererProps } from "@/types/renderer";

const ChatConversationRenderer: FC<ChatConversationRendererProps> = ({
  content,
}) => {
  const { conversation_id } = parse(content);
  const { agentStore } = useAgentStore();
  const currentConversation = agentStore[conversation_id];

  if (!currentConversation) return null;

  return (
    <ChatThreadArea threads={currentConversation.threads} isStreaming={false} />
  );
};

export default memo(ChatConversationRenderer);
