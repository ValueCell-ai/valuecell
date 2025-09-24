import { ArrowUp, MessageCircle, Settings } from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";
import { Navigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import ScrollTextarea, {
  type ScrollTextareaRef,
} from "@/components/valuecell/scroll/scroll-textarea";
import { useSSE } from "@/hooks/use-sse";
import { updateAgentConversationsStore } from "@/lib/agent-store";
import { getServerUrl } from "@/lib/api-client";
import { SSEReadyState } from "@/lib/sse-client";
import { cn } from "@/lib/utils";
import { agentData } from "@/mock/agent-data";
import type {
  AgentConversationsStore,
  AgentStreamRequest,
  SSEData,
  ThreadView,
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
  const agent = agentData[agentName ?? ""];

  const textareaRef = useRef<ScrollTextareaRef>(null);
  const [inputValue, setInputValue] = useState("");

  // Use optimized reducer for state management
  const [agentStore, dispatchAgentStore] = useReducer(agentStoreReducer, {});
  const curConversationId = useRef<string>("");
  const curThreadId = useRef<string>("");
  const [isSending, setIsSending] = useState(false);
  const [shouldClose, setShouldClose] = useState(false);

  // Get current conversation
  const threadEntries = useMemo(() => {
    if (!curConversationId.current || !agentStore[curConversationId.current]) {
      return null;
    }
    const threads = agentStore[curConversationId.current].threads;
    return threads
      ? (Object.entries(threads) as Array<[string, ThreadView]>)
      : [];
  }, [agentStore]);

  // Handle SSE data events using agent store
  const handleSSEData = useCallback(
    (sseData: SSEData) => {
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
          dispatchAgentStore({
            event: "message_chunk",
            data: {
              conversation_id: curConversationId.current,
              thread_id: data.thread_id,
              task_id: "",
              subtask_id: "",
              payload: { content: inputValue.trim() },
              role: "user",
            },
          });

          setInputValue("");
          break;
        }

        case "done": {
          curThreadId.current = data.thread_id;
          setShouldClose(true);
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
    },
    [inputValue],
  );

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
        setIsSending(false); // Reset sending state on open
      },
      onError: (error: Error) => {
        console.error("❌ SSE connection error:", error);
        setIsSending(false); // Reset sending state on error
      },
      onClose: () => {
        console.log("🔌 SSE connection closed");
        setIsSending(false); // Reset sending state on close
      },
    },
  });

  useEffect(() => {
    if (shouldClose) {
      close();
      setShouldClose(false);
    }
  }, [shouldClose]);

  // Derived state - compute from existing state instead of maintaining separately
  const isConnected = state === SSEReadyState.OPEN;
  const isConnecting = state === SSEReadyState.CONNECTING;
  // isStreaming represents when AI is processing/responding, not related to user input requirements
  const isStreaming = isConnected && isSending;

  // Send message to agent
  const sendMessage = useCallback(
    async (message: string) => {
      // Prevent duplicate sends
      if (isSending || isConnecting) {
        console.log(
          "Already sending or connecting, ignoring duplicate request",
        );
        return;
      }

      setIsSending(true);

      try {
        const request: AgentStreamRequest = {
          query: message,
          agent_name: agent.name,
          conversation_id: curConversationId.current,
        };

        // Connect SSE client with request body to receive streaming response
        await connect(JSON.stringify(request));
      } catch (error) {
        console.error("Failed to send message:", error);
        setIsSending(false); // Reset immediately on error
      }
    },
    [connect, isSending, isConnecting, agentName],
  );

  const handleSendMessage = useCallback(() => {
    const trimmedInput = inputValue.trim();
    // Prevent sending while connecting/sending or when input is empty
    if (!trimmedInput || isConnecting || isSending) {
      console.log("Cannot send: empty input, connecting, or already sending");
      return;
    }

    // Always use sendMessage - user input for plan_require_user_input is just normal conversation
    sendMessage(trimmedInput);
  }, [inputValue, isConnecting, isSending, sendMessage]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!agent) return <Navigate to="/" replace />;

  // Agent skills/tags
  const agentSkills = [
    "Hong Kong stocks",
    "US stocks",
    "Predictive analysis",
    "Stock selection",
  ];

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header with agent info and actions */}
      <header className="flex items-center justify-between border-gray-100 border-b p-6">
        <div className="flex items-center gap-4">
          {/* Agent Avatar */}
          <div className="relative size-12">
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg" />
            <div className="absolute inset-0.5 flex items-center justify-center rounded-full bg-white">
              <span className="font-semibold text-gray-700 text-sm">AI</span>
            </div>
          </div>

          {/* Agent Info */}
          <div className="flex flex-col gap-1">
            <h1 className="font-semibold text-gray-950 text-lg">
              AI Hedge Fund Agent
            </h1>
            <div className="flex items-center gap-2">
              {agentSkills.slice(0, 2).map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 font-medium text-blue-700 text-xs"
                >
                  {skill}
                </span>
              ))}
              {agentSkills.length > 2 && (
                <span className="text-gray-500 text-xs">
                  +{agentSkills.length - 2} more
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="size-9 rounded-lg hover:bg-gray-100"
          >
            <MessageCircle size={18} className="text-gray-600" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-9 rounded-lg hover:bg-gray-100"
          >
            <Settings size={18} className="text-gray-600" />
          </Button>
        </div>
      </header>

      {/* Main content area */}
      <main className="relative flex flex-1 flex-col">
        {!threadEntries?.length ? (
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
                  disabled={isStreaming || isSending}
                />
                <Button
                  size="icon"
                  className="size-8 cursor-pointer self-end rounded-full"
                  onClick={handleSendMessage}
                  disabled={isStreaming || isSending || !inputValue.trim()}
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
            {/* Chat messages with optimized rendering */}
            <div className="flex-1 space-y-6 overflow-y-auto p-6">
              {threadEntries.map(([threadId, thread], threadIndex) => {
                return (
                  <div key={threadId} className="space-y-6">
                    {threadEntries.length > 1 && (
                      <div className="flex items-center gap-2 text-gray-400 text-xs uppercase tracking-wide">
                        <span className="h-px flex-1 bg-gray-200" />
                        <span>Thread {threadIndex + 1}</span>
                        <span className="h-px flex-1 bg-gray-200" />
                      </div>
                    )}

                    {thread.messages.map((message, index) => (
                      <ChatMessageComponent
                        key={`${message.conversation_id}-${threadId}-${index}`}
                        message={message}
                        index={index}
                        conversationId={curConversationId.current}
                        threadId={threadId}
                      />
                    ))}
                  </div>
                );
              })}

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
            </div>

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
                  disabled={isStreaming || isSending}
                />
                <Button
                  size="icon"
                  className="size-8 cursor-pointer self-end rounded-full"
                  onClick={handleSendMessage}
                  disabled={isStreaming || isSending || !inputValue.trim()}
                >
                  <ArrowUp size={16} className="text-white" />
                </Button>
              </div>

              {/* Status indicators */}
              <div className="mt-2 flex items-center justify-between text-gray-500 text-xs">
                <div className="flex items-center gap-4">
                  <span
                    className={cn(
                      "flex items-center gap-1",
                      isStreaming
                        ? "text-green-600"
                        : isConnecting
                          ? "text-blue-600"
                          : isConnected
                            ? "text-green-600"
                            : "text-red-600",
                    )}
                  >
                    <div
                      className={cn(
                        "h-2 w-2 rounded-full",
                        isStreaming
                          ? "bg-green-500"
                          : isConnecting
                            ? "animate-pulse bg-blue-500"
                            : isConnected
                              ? "bg-green-500"
                              : "bg-red-500",
                      )}
                    />
                    <span className="text-xs">
                      {isStreaming
                        ? "Streaming"
                        : isConnecting
                          ? "Connecting"
                          : isConnected
                            ? "Ready"
                            : "Disconnected"}
                    </span>
                  </span>
                  {curConversationId.current && (
                    <span>Session: {curConversationId.current}</span>
                  )}
                  {curThreadId.current && (
                    <span>Thread: {curThreadId.current}</span>
                  )}
                </div>
                <span>Press Enter to send, Shift+Enter for new line</span>
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
