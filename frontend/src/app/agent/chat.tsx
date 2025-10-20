import { useCallback } from "react";
import { Navigate, useParams } from "react-router";
import { toast } from "sonner";
import { useGetAgentInfo } from "@/api/agent";
import { useSSE } from "@/hooks/use-sse";
import { getServerUrl } from "@/lib/api-client";
import {
  AgentStoreProvider,
  useAgentStore,
} from "@/provider/agent-store-provider";
import type { AgentStreamRequest, SSEData } from "@/types/agent";
import type { Route } from "./+types/chat";
import ChatConversationArea from "./components/chat-conversation/chat-conversation-area";

function AgentChatContent() {
  const { agentName } = useParams<Route.LoaderArgs["params"]>();
  const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });

  // Use agent store from context
  const {
    agentStore,
    dispatchAgentStore,
    curConversationId,
    setCurConversationId,
    currentConversation,
    curThreadId,
  } = useAgentStore();
  console.log("🚀 ~ AgentChatContent ~ agentStore:", agentStore);

  // Handle SSE data events using agent store
  // biome-ignore lint/correctness/useExhaustiveDependencies: close is no need to be in dependencies
  const handleSSEData = useCallback((sseData: SSEData) => {
    // Update agent store using the reducer
    dispatchAgentStore(sseData);

    // Handle specific UI state updates
    const { event, data } = sseData;
    switch (event) {
      case "conversation_started":
        setCurConversationId(data.conversation_id);
        break;

      case "thread_started":
        curThreadId.current = data.thread_id;
        break;

      case "system_failed":
        // Handle system errors in UI layer
        toast.error(data.payload.content, {
          closeButton: true,
          duration: 30 * 1000,
        });
        break;

      case "done":
        close();
        break;

      // All message-related events are handled by the store
      default:
        // Update current thread ID for message events
        if ("thread_id" in data) {
          curThreadId.current = data.thread_id;
        }
        break;
    }
  }, []);

  // Initialize SSE connection using the useSSE hook
  const { connect, close, isStreaming } = useSSE({
    url: getServerUrl("/agents/stream"),
    handlers: {
      onData: handleSSEData,
      onOpen: () => {
        console.log("✅ SSE connection opened");
      },
      onError: (error: Error) => {
        console.error("❌ SSE connection error:", error);
      },
      onClose: () => {
        console.log("🔌 SSE connection closed");
      },
    },
  });

  // Send message to agent
  // biome-ignore lint/correctness/useExhaustiveDependencies: connect is no need to be in dependencies
  const sendMessage = useCallback(
    async (message: string) => {
      try {
        const request: AgentStreamRequest = {
          query: message,
          agent_name: agentName ?? "",
          conversation_id: curConversationId,
        };

        // Connect SSE client with request body to receive streaming response
        await connect(JSON.stringify(request));
      } catch (error) {
        console.error("Failed to send message:", error);
      }
    },
    [agentName, curConversationId],
  );

  if (isLoadingAgent) return null;
  if (!agent) return <Navigate to="/" replace />;

  return (
    <main className="relative flex flex-1 flex-col overflow-hidden">
      <ChatConversationArea
        agent={agent}
        currentConversation={currentConversation}
        isStreaming={isStreaming}
        sendMessage={sendMessage}
      />
    </main>
  );
}

export default function AgentChat() {
  const { agentName } = useParams<Route.LoaderArgs["params"]>();

  return (
    <AgentStoreProvider agentName={agentName ?? ""}>
      <AgentChatContent />
    </AgentStoreProvider>
  );
}
