import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect } from "react";
import {
  Navigate,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router";
import { toast } from "sonner";
import { useGetAgentInfo } from "@/api/agent";
import { useGetConversationHistory, usePollTaskList } from "@/api/conversation";
import { API_QUERY_KEYS } from "@/constants/api";
import { useSSE } from "@/hooks/use-sse";
import { getServerUrl } from "@/lib/api-client";
import {
  useAgentStoreActions,
  useCurrentConversation,
} from "@/store/agent-store";
import type { AgentStreamRequest, SSEData } from "@/types/agent";
import type { Route } from "./+types/chat";
import ChatConversationArea from "./components/chat-conversation/chat-conversation-area";

export default function AgentChat() {
  const { agentName } = useParams<Route.LoaderArgs["params"]>();
  const conversationId = useSearchParams()[0].get("id") ?? "";
  const navigate = useNavigate();
  const inputValue = useLocation().state?.inputValue;

  // Use optimized hooks with built-in shallow comparison
  const { curConversation, curConversationId } = useCurrentConversation();
  const {
    dispatchAgentStore,
    setCurConversationId,
    dispatchAgentStoreHistory,
  } = useAgentStoreActions();

  const queryClient = useQueryClient();
  const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });
  const { data: conversationHistory } =
    useGetConversationHistory(conversationId);
  const { data: taskList } = usePollTaskList(conversationId);

  // Load conversation history (only once when conversation changes)
  useEffect(() => {
    if (
      !conversationId ||
      !conversationHistory ||
      conversationHistory.length === 0
    )
      return;

    dispatchAgentStoreHistory(conversationId, conversationHistory, true);
  }, [conversationId, conversationHistory, dispatchAgentStoreHistory]);

  // Update task list (polls every 30s)
  useEffect(() => {
    if (!conversationId || !taskList || taskList.length === 0) return;

    dispatchAgentStoreHistory(conversationId, taskList);
  }, [conversationId, taskList, dispatchAgentStoreHistory]);

  // Handle SSE data events using agent store
  // biome-ignore lint/correctness/useExhaustiveDependencies: close is no need to be in dependencies
  const handleSSEData = useCallback((sseData: SSEData) => {
    // Update agent store using the reducer
    dispatchAgentStore(sseData);

    // Handle specific UI state updates
    const { event, data } = sseData;
    switch (event) {
      case "conversation_started":
        navigate(`/agent/${agentName}?id=${data.conversation_id}`, {
          replace: true,
        });
        queryClient.invalidateQueries({
          queryKey: API_QUERY_KEYS.CONVERSATION.conversationList,
        });
        break;

      case "component_generator":
        if (data.payload.component_type === "subagent_conversation") {
          queryClient.invalidateQueries({
            queryKey: API_QUERY_KEYS.CONVERSATION.conversationList,
          });
        }
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
          conversation_id: conversationId,
        };

        // Connect SSE client with request body to receive streaming response
        await connect(JSON.stringify(request));
      } catch (error) {
        console.error("Failed to send message:", error);
      }
    },
    [agentName, conversationId],
  );

  useEffect(() => {
    if (curConversationId !== conversationId) {
      setCurConversationId(conversationId);
    }

    if (inputValue) {
      sendMessage(inputValue);
      // Clear the state after using it once to prevent re-triggering on page refresh
      navigate(".", { replace: true, state: {} });
    }
  }, [
    conversationId,
    inputValue,
    sendMessage,
    setCurConversationId,
    curConversationId,
    navigate,
  ]);

  if (isLoadingAgent) return null;
  if (!agent) return <Navigate to="/" replace />;

  return (
    <main className="relative flex flex-1 flex-col overflow-hidden">
      <ChatConversationArea
        agent={agent}
        currentConversation={curConversation}
        isStreaming={isStreaming}
        sendMessage={sendMessage}
      />
    </main>
  );
}
