import { useQueryClient } from "@tanstack/react-query";
import { type FC, memo, useCallback, useEffect, useState } from "react";
import {
  Navigate,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router";
import { toast } from "sonner";
import { useGetAgentInfo } from "@/api/agent";
import { useGetConversationHistory, usePollTaskList } from "@/api/conversation";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { API_QUERY_KEYS } from "@/constants/api";
import useSSE from "@/hooks/use-sse";
import { getServerUrl } from "@/lib/api-client";
import { tracker } from "@/lib/tracker";
import {
  MultiSectionProvider,
  useMultiSection,
} from "@/provider/multi-section-provider";
import {
  useAgentStoreActions,
  useCurrentConversation,
} from "@/store/agent-store";
import type {
  AgentStreamRequest,
  AgentViewProps,
  MultiSectionComponentType,
  SectionComponentType,
  SSEData,
} from "@/types/agent";
import {
  ChatConversationHeader,
  ChatInputArea,
  ChatMultiSectionComponent,
  ChatSectionComponent,
  ChatThreadArea,
  ChatWelcomeScreen,
} from "../chat-conversation";

interface CommonAgentAreaProps {
  agentName: string;
}

const CommonAgentAreaContent: FC<CommonAgentAreaProps> = ({ agentName }) => {
  const { data: agent, isLoading: isLoadingAgent } = useGetAgentInfo({
    agentName: agentName ?? "",
  });

  const conversationId = useSearchParams()[0].get("id") ?? "";
  const navigate = useNavigate();
  const inputValueFromLocation = useLocation().state?.inputValue;

  // Use optimized hooks with built-in shallow comparison
  const { curConversation, curConversationId } = useCurrentConversation();
  const {
    dispatchAgentStore,
    setCurConversationId,
    dispatchAgentStoreHistory,
  } = useAgentStoreActions();

  const queryClient = useQueryClient();

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

  // Initialize SSE connection using the useSSE hook
  const { connect, close, isStreaming } = useSSE({
    url: getServerUrl("/agents/stream"),
    handlers: {
      onData: (sseData: SSEData) => {
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
      },
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
          agent_name: agentName,
          conversation_id: conversationId,
        };

        tracker.send("use", {
          agent_name: agentName,
        });

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

    if (inputValueFromLocation) {
      sendMessage(inputValueFromLocation);
      // Clear the state after using it once to prevent re-triggering on page refresh
      navigate(".", { replace: true, state: {} });
    }
  }, [
    sendMessage,
    setCurConversationId,
    curConversationId,
    navigate,
    conversationId,
    inputValueFromLocation,
  ]);

  const [inputValue, setInputValue] = useState<string>("");
  const { currentSection } = useMultiSection();

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim()) return;
    try {
      await sendMessage(inputValue);
      setInputValue("");
    } catch (error) {
      // Keep input value on error so user doesn't lose their text
      console.error("Failed to send message:", error);
    }
  }, [inputValue, sendMessage]);

  const handleInputChange = useCallback((value: string) => {
    setInputValue(value);
  }, []);

  if (isLoadingAgent) return null;
  if (!agent) return <Navigate to="/" replace />;

  // Check if conversation has any messages
  const hasMessages =
    curConversation?.threads && Object.keys(curConversation.threads).length > 0;

  if (!hasMessages) {
    return (
      <>
        <ChatConversationHeader agent={agent} />
        <ChatWelcomeScreen
          title={`Welcome to ${agent.display_name}!`}
          inputValue={inputValue}
          onInputChange={handleInputChange}
          onSendMessage={handleSendMessage}
          disabled={isStreaming}
        />
      </>
    );
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* main section */}
      <section className="flex flex-1 flex-col items-center">
        <ChatConversationHeader agent={agent} />

        <ChatThreadArea
          threads={curConversation.threads}
          isStreaming={isStreaming}
        />

        {/* Input area now only in main section */}
        <ChatInputArea
          className="main-chat-area mb-8"
          value={inputValue}
          onChange={handleInputChange}
          onSend={handleSendMessage}
          placeholder="Type your message..."
          disabled={isStreaming}
          variant="chat"
        />
      </section>

      {/* Chat section components: one section per special component_type */}
      {Object.entries(curConversation.sections).map(
        ([componentType, threadView]) => {
          return (
            <ChatSectionComponent
              key={componentType}
              // TODO: componentType as type assertion is not safe, find a better way to do this
              componentType={componentType as SectionComponentType}
              threadView={threadView}
            />
          );
        },
      )}

      {/* Multi-section detail view */}
      {currentSection && (
        <section className="flex flex-1 flex-col py-4">
          <ScrollContainer>
            <ChatMultiSectionComponent
              componentType={
                // only the component_type is the same as the MultiSectionComponentType
                currentSection.component_type as MultiSectionComponentType
              }
              content={currentSection.payload.content}
            />
          </ScrollContainer>
        </section>
      )}
    </div>
  );
};

const CommonAgentArea: FC<AgentViewProps> = (props) => {
  return (
    <MultiSectionProvider>
      <CommonAgentAreaContent {...props} />
    </MultiSectionProvider>
  );
};

export default memo(CommonAgentArea);
