import { ArrowUp, MessageCircle, Settings } from "lucide-react";
import { useCallback, useMemo, useReducer, useRef, useState } from "react";
import { useParams } from "react-router";
import { useGetAgentInfo } from "@/api/agent";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import ScrollTextarea, {
  type ScrollTextareaRef,
} from "@/components/valuecell/scroll/scroll-textarea";
import { useSSE } from "@/hooks/use-sse";
import { updateAgentConversationsStore } from "@/lib/agent-store";
import { getServerUrl } from "@/lib/api-client";
import { SSEReadyState } from "@/lib/sse-client";
import { cn } from "@/lib/utils";
import type {
  AgentConversationsStore,
  AgentStreamRequest,
  SSEData,
} from "@/types/agent";
import type { Route } from "./+types/chat";
import { ChatBackground } from "./components";
import { ChatMessage as ChatMessageComponent } from "./components/chat-message";

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

  const textareaRef = useRef<ScrollTextareaRef>(null);
  const [inputValue, setInputValue] = useState("");

  // Use optimized reducer for state management
  const [agentStore, dispatchAgentStore] = useReducer(agentStoreReducer, {});
  console.log("🚀 ~ AgentChat ~ agentStore:", agentStore);
  const curConversationId = useRef<string>("");
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
      case "conversation_started": {
        curConversationId.current = data.conversation_id;
        break;
      }

      case "thread_started": {
        curThreadId.current = data.thread_id;
        setInputValue("");
        break;
      }

      case "done": {
        close();
        break;
      }

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
  const {
    connect,
    close,
    state,
    error: sseError,
  } = useSSE({
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

  const isStreaming = useMemo(
    () => state === SSEReadyState.OPEN || state === SSEReadyState.CONNECTING,
    [state],
  );

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

  const handleSendMessage = useCallback(() => {
    const trimmedInput = inputValue.trim();
    // Prevent sending while connecting/sending or when input is empty
    if (!trimmedInput || isStreaming) {
      console.log("Cannot send: empty input, connecting, or already sending");
      return;
    }

    // Always use sendMessage - user input for plan_require_user_input is just normal conversation
    sendMessage(trimmedInput);
  }, [inputValue, isStreaming, sendMessage]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send message on Enter key (excluding Shift+Enter line breaks and IME composition state)
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSendMessage();
    }
  };

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
        {!currentConversation?.threads ||
        Object.keys(currentConversation.threads).length === 0 ? (
          <>
            {/* Background blur effects for welcome screen */}
            <ChatBackground />

            {/* Welcome content */}
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
              <h1 className="text-center font-semibold text-2xl text-gray-950 leading-12">
                Welcome to AI hedge fund agent！
              </h1>

              {/* Input card */}
              <div
                className={cn(
                  "flex w-2/3 min-w-[600px] flex-col gap-2 rounded-2xl bg-white p-4",
                  "border border-gray-200 shadow-[0px_4px_20px_8px_rgba(17,17,17,0.04)]",
                  "focus-within:border-gray-300 focus-within:shadow-[0px_4px_20px_8px_rgba(17,17,17,0.08)]",
                )}
              >
                <ScrollTextarea
                  ref={textareaRef}
                  value={inputValue}
                  onInput={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="You can inquire and analyze the trend of NVIDIA in the next three months"
                  maxHeight={120}
                  minHeight={24}
                  disabled={isStreaming}
                />
                <Button
                  size="icon"
                  className="size-8 cursor-pointer self-end rounded-full"
                  onClick={handleSendMessage}
                  disabled={isStreaming || !inputValue.trim()}
                >
                  <ArrowUp size={16} className="text-white" />
                </Button>
              </div>

              {/* Connection status */}
              {sseError && (
                <div className="flex items-center gap-2 text-red-600 text-sm">
                  <span>⚠️ Connection error: {sseError.message}</span>
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            {/* Chat messages using original data structure */}
            <ScrollContainer className="flex-1 space-y-6 p-6">
              {currentConversation &&
                Object.entries(currentConversation.threads).map(
                  ([threadId, thread], threadIndex) => {
                    const threadCount = Object.keys(
                      currentConversation.threads,
                    ).length;
                    const showThreadSeparator =
                      threadIndex > 0 && threadCount > 1;

                    return (
                      <div key={threadId} className="space-y-6">
                        {/* Thread separator - only show for subsequent threads when there are multiple threads */}
                        {showThreadSeparator && (
                          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide">
                            <span className="h-px flex-1 bg-gray-200" />
                            <span>Thread {threadId}</span>
                            <span className="h-px flex-1 bg-gray-200" />
                          </div>
                        )}

                        {/* Render all tasks within this thread */}
                        {Object.entries(thread.tasks).map(([taskId, task]) => {
                          if (task.items && task.items.length > 0) {
                            return (
                              <ChatMessageComponent
                                key={taskId}
                                items={task.items}
                              />
                            );
                          }
                          return null;
                        })}
                      </div>
                    );
                  },
                )}

              {/* Streaming indicator */}
              {isStreaming && (
                <div className="flex items-center gap-2 text-gray-500 text-sm">
                  <div className="flex space-x-1">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-0" />
                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-150" />
                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-300" />
                  </div>
                  <span>AI is thinking...</span>
                </div>
              )}
            </ScrollContainer>

            {/* Input area at bottom */}
            <div className="border-gray-200 border-t p-4">
              <div
                className={cn(
                  "flex w-full flex-col gap-2 rounded-2xl bg-white p-4",
                  "border border-gray-200 shadow-[0px_4px_20px_8px_rgba(17,17,17,0.04)]",
                  "focus-within:border-gray-300 focus-within:shadow-[0px_4px_20px_8px_rgba(17,17,17,0.08)]",
                )}
              >
                <ScrollTextarea
                  ref={textareaRef}
                  value={inputValue}
                  onInput={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your message..."
                  maxHeight={120}
                  minHeight={24}
                  disabled={isStreaming}
                />
                <Button
                  size="icon"
                  className="size-8 cursor-pointer self-end rounded-full"
                  onClick={handleSendMessage}
                  disabled={isStreaming}
                >
                  <ArrowUp size={16} className="text-white" />
                </Button>
              </div>

              {sseError && (
                <div className="mt-2 rounded border border-red-200 bg-red-50 p-2 text-red-600 text-sm">
                  Error: {sseError.message}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
