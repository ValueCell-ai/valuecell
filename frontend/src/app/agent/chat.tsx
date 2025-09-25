import { MessageCircle, Settings } from "lucide-react";
import { useCallback, useMemo, useReducer, useRef } from "react";
import { useParams } from "react-router";
import { useGetAgentInfo } from "@/api/agent";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useSSE } from "@/hooks/use-sse";
import { updateAgentConversationsStore } from "@/lib/agent-store";
import { getServerUrl } from "@/lib/api-client";
import type {
  AgentConversationsStore,
  AgentStreamRequest,
  SSEData,
} from "@/types/agent";
import type { Route } from "./+types/chat";
import ChatConversationView from "./components/chat-conversation-view";

// Optimized reducer for agent store management
function agentStoreReducer(
  state: AgentConversationsStore,
  action: SSEData,
): AgentConversationsStore {
  return updateAgentConversationsStore(state, action);
}

export default function AgentChat() {
  const { agentName } = useParams<Route.LoaderArgs["params"]>();
  const { data: agent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });

  // Use optimized reducer for state management
  const [agentStore, dispatchAgentStore] = useReducer(agentStoreReducer, {});
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
  console.log("🚀 ~ AgentChat ~ isStreaming:", isStreaming);

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

  // if (!agent) return <Navigate to="/" replace />;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header with agent info and actions */}
      <header className="flex items-center justify-between border-gray-100 border-b p-6">
        <div className="flex items-center gap-4">
          {/* Agent Avatar */}
          <Avatar className="size-14">
            <AvatarImage src={agent?.icon_url} />
            <AvatarFallback>{agentName?.slice(0, 2)}</AvatarFallback>
          </Avatar>

          {/* Agent Info */}
          <div className="flex flex-col gap-1.5">
            <h1 className="font-semibold text-gray-950 text-lg">{agentName}</h1>
            <div className="flex items-center gap-1">
              {agent?.agent_metadata.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-nowrap rounded-md bg-gray-100 px-3 py-1 font-normal text-gray-700 text-xs"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            className="size-8 cursor-pointer rounded-lg"
            size="icon"
          >
            <MessageCircle size={16} className="text-gray-700" />
          </Button>
          <Button
            variant="secondary"
            className="size-8 cursor-pointer rounded-lg"
            size="icon"
          >
            <Settings size={16} className="text-gray-700" />
          </Button>
        </div>
      </header>

      {/* Main content area */}
      <main className="relative flex flex-1 flex-col overflow-hidden">
        <ChatConversationView
          currentConversation={currentConversation}
          isStreaming={isStreaming}
          sendMessage={sendMessage}
        />
      </main>
    </div>
  );
}
