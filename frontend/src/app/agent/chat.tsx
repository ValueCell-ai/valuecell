import { useCallback, useMemo, useReducer, useRef } from "react";
import { Navigate, useParams } from "react-router";
import { useGetAgentInfo } from "@/api/agent";
import { useSSE } from "@/hooks/use-sse";
import { updateAgentConversationsStore } from "@/lib/agent-store";
import { getServerUrl } from "@/lib/api-client";
import type {
  AgentConversationsStore,
  AgentStreamRequest,
  SSEData,
} from "@/types/agent";
import type { Route } from "./+types/chat";
import ChatConversationArea from "./components/chat-conversation/chat-conversation-area";

// Optimized reducer for agent store management
function agentStoreReducer(
  state: AgentConversationsStore,
  action: SSEData,
): AgentConversationsStore {
  return updateAgentConversationsStore(state, action);
}

export default function AgentChat() {
  const { agentName } = useParams<Route.LoaderArgs["params"]>();
  const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });

  // Use optimized reducer for state management
  const [agentStore, dispatchAgentStore] = useReducer(agentStoreReducer, {});
  console.log("🚀 ~ AgentChat ~ agentStore:", agentStore);
  // TODO: temporary conversation id (after will remove hardcoded)
  const curConversationId = useRef<string>(`${agentName}_conv_default_user`);
  const curThreadId = useRef<string>("");

  // Get current conversation using original data structure
  const currentConversation = useMemo(() => {
    return curConversationId.current in agentStore
      ? agentStore[curConversationId.current]
      : null;
  }, [agentStore]);

  // Handle SSE data events using agent store
  // biome-ignore lint/correctness/useExhaustiveDependencies: close is no need to be in dependencies
  const handleSSEData = useCallback((sseData: SSEData) => {
    // Update agent store using the reducer
    dispatchAgentStore(sseData);

    // Handle specific UI state updates
    const { event, data } = sseData;
    switch (event) {
      case "conversation_started":
        curConversationId.current = data.conversation_id;
        break;

      case "thread_started":
        curThreadId.current = data.thread_id;
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
          conversation_id: curConversationId.current,
        };

        // Connect SSE client with request body to receive streaming response
        await connect(JSON.stringify(request));
      } catch (error) {
        console.error("Failed to send message:", error);
      }
    },
    [agentName],
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
