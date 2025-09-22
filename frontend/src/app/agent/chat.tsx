import {
  AlertTriangle,
  ArrowUp,
  BarChart3,
  Bot,
  Brain,
  CheckCircle,
  Clock,
  FileText,
  MessageCircle,
  Settings,
  Table,
  User,
  Zap,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { Navigate, useParams } from "react-router";
import { Button } from "@/components/ui/button";
import ScrollTextarea, {
  type ScrollTextareaRef,
} from "@/components/valuecell/scroll/scroll-textarea";
import { useSSE } from "@/hooks/use-sse";
import { cn } from "@/lib/utils";
import { agentData } from "@/mock/agent-data";
import type {
  AgentEventMap,
  AgentStreamRequest,
  ChatMessage,
  GeneratedComponent,
} from "@/types/agent";
import {
  COMPONENT_TYPE,
  type ComponentType,
  MESSAGE_TYPE,
  TOOL_CALL_STATUS,
} from "@/types/agent";
import type { Route } from "./+types/chat";
import { ChatBackground } from "./components";

export default function AgentChat() {
  const { agentId } = useParams<Route.LoaderArgs["params"]>();
  const textareaRef = useRef<ScrollTextareaRef>(null);
  const [inputValue, setInputValue] = useState("");

  // Simplified chat state - only essential state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [userInputRequired, setUserInputRequired] = useState<string | null>(
    null,
  );

  // Optimized message update helper
  const updateOrCreateMessage = useCallback(
    (
      messageId: string,
      content: string,
      isComplete: boolean,
      threadId: string,
      taskId?: string,
      subtaskId?: string,
      isAppend = false,
    ) => {
      setMessages((prevMessages) => {
        const updatedMessages = [...prevMessages];
        const messageIndex = updatedMessages.findIndex(
          (msg) => msg.id === messageId,
        );

        if (messageIndex >= 0) {
          updatedMessages[messageIndex] = {
            ...updatedMessages[messageIndex],
            content: isAppend
              ? updatedMessages[messageIndex].content + content
              : content,
            isComplete,
          };
        } else {
          updatedMessages.push({
            id: messageId,
            content,
            type: MESSAGE_TYPE.ASSISTANT,
            isComplete,
            threadId,
            taskId,
            subtaskId,
          });
        }

        return updatedMessages;
      });

      setCurrentThreadId(threadId);
    },
    [],
  );

  // Handle SSE events with automatic type inference
  const handleSSEEvent = useCallback(
    <T extends keyof AgentEventMap>(eventType: T, data: AgentEventMap[T]) => {
      switch (eventType) {
        case "conversation_started": {
          const payload = data as AgentEventMap["conversation_started"];
          setConversationId(payload.conversation_id);
          break;
        }

        case "message_chunk": {
          const payload = data as AgentEventMap["message_chunk"];
          const messageId = `${payload.conversation_id}-${payload.thread_id}`;
          updateOrCreateMessage(
            messageId,
            payload.data.content,
            false,
            payload.thread_id,
            payload.task_id,
            payload.subtask_id,
            true, // append content
          );
          break;
        }

        case "message": {
          const payload = data as AgentEventMap["message"];
          const messageId = `${payload.conversation_id}-${payload.thread_id}`;
          updateOrCreateMessage(
            messageId,
            payload.data.content,
            true,
            payload.thread_id,
            payload.task_id,
            payload.subtask_id,
            false, // replace content
          );
          break;
        }

        case "component_generator": {
          const payload = data as AgentEventMap["component_generator"];
          const componentMessage: ChatMessage = {
            id: `component-${payload.conversation_id}-${payload.thread_id}-${Date.now()}`,
            content: "",
            type: MESSAGE_TYPE.COMPONENT,
            isComplete: true,
            threadId: payload.thread_id,
            taskId: payload.task_id,
            subtaskId: payload.subtask_id,
            component: {
              type: payload.data.component_type as ComponentType,
              content: payload.data.content,
            },
          };

          setMessages((prev) => [...prev, componentMessage]);
          break;
        }

        case "plan_require_user_input": {
          const payload = data as AgentEventMap["plan_require_user_input"];
          setUserInputRequired(payload.data.content);
          break;
        }

        case "tool_call_started":
        case "tool_call_completed": {
          const payload = data as
            | AgentEventMap["tool_call_started"]
            | AgentEventMap["tool_call_completed"];
          const messageId = `${payload.conversation_id}-${payload.thread_id}`;
          const isCompleted = eventType === "tool_call_completed";

          setMessages((prevMessages) => {
            const updatedMessages = [...prevMessages];
            const messageIndex = updatedMessages.findIndex(
              (msg) => msg.id === messageId,
            );

            if (messageIndex >= 0) {
              const message = updatedMessages[messageIndex];
              const toolCalls = [...(message.toolCalls || [])];
              const toolCallIndex = toolCalls.findIndex(
                (tc) => tc.id === payload.data.tool_call_id,
              );

              const toolCallData = {
                id: payload.data.tool_call_id,
                name: payload.data.tool_name,
                status: isCompleted
                  ? TOOL_CALL_STATUS.COMPLETED
                  : TOOL_CALL_STATUS.STARTED,
                startTime: new Date(),
                ...(isCompleted && {
                  result: (payload as AgentEventMap["tool_call_completed"]).data
                    .tool_call_result,
                  endTime: new Date(),
                }),
              };

              if (toolCallIndex >= 0) {
                toolCalls[toolCallIndex] = {
                  ...toolCalls[toolCallIndex],
                  ...toolCallData,
                };
              } else {
                toolCalls.push(toolCallData);
              }

              updatedMessages[messageIndex] = { ...message, toolCalls };
            }

            return updatedMessages;
          });
          break;
        }

        case "reasoning": {
          const payload = data as AgentEventMap["reasoning"];
          const messageId = `${payload.conversation_id}-${payload.thread_id}`;

          setMessages((prevMessages) => {
            const updatedMessages = [...prevMessages];
            const messageIndex = updatedMessages.findIndex(
              (msg) => msg.id === messageId,
            );

            if (messageIndex >= 0) {
              updatedMessages[messageIndex] = {
                ...updatedMessages[messageIndex],
                reasoning: payload.data.content,
              };
            }

            return updatedMessages;
          });
          break;
        }

        case "plan_failed":
        case "task_failed": {
          const payload = data as
            | AgentEventMap["plan_failed"]
            | AgentEventMap["task_failed"];
          const errorMessage: ChatMessage = {
            id: `error-${payload.conversation_id}-${payload.thread_id}-${Date.now()}`,
            content: payload.data.content,
            type: MESSAGE_TYPE.ERROR,
            isComplete: true,
            threadId: payload.thread_id,
          };

          setMessages((prev) => [...prev, errorMessage]);
          break;
        }

        case "done": {
          const payload = data as AgentEventMap["done"];
          setUserInputRequired(null);
          setCurrentThreadId(payload.thread_id);
          break;
        }
      }
    },
    [updateOrCreateMessage],
  );

  // Initialize SSE connection using the useSSE hook
  const {
    connect,
    isConnected,
    isConnecting,
    error: sseError,
  } = useSSE<AgentEventMap>({
    options: {
      url: "http://localhost:8001/api/v1/agents/stream",
      headers: {
        "Content-Type": "application/json",
      },
      autoReconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      timeout: 30000,
    },
    handlers: {
      onEvent: handleSSEEvent,
      onOpen: () => {
        console.log("SSE connection opened");
      },
      onError: (error) => {
        console.error("SSE connection error:", error);
      },
      onClose: () => {
        console.log("SSE connection closed");
      },
      onReconnect: (attempt) => {
        console.log(`Reconnecting to agent stream (attempt ${attempt})`);
      },
    },
  });

  // Derived state - compute from existing state instead of maintaining separately
  const isStreaming = isConnected && !userInputRequired;

  // Send message to agent
  const sendMessage = useCallback(
    async (message: string) => {
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        content: message,
        type: MESSAGE_TYPE.USER,
        isComplete: true,
      };

      setMessages((prev) => [...prev, userMessage]);
      setUserInputRequired(null);

      try {
        const request: AgentStreamRequest = {
          query: message,
          agent_name: "SecAgent", // You can make this dynamic based on the agent
          conversation_id: conversationId || undefined,
          thread_id: currentThreadId || undefined,
        };

        // Connect SSE client with request body to receive streaming response
        await connect(JSON.stringify(request));
      } catch (error) {
        console.error("Failed to send message:", error);
      }
    },
    [conversationId, currentThreadId, connect],
  );

  // Handle user input for plan_require_user_input events
  const handleUserInputResponse = useCallback(
    async (response: string) => {
      await sendMessage(response);
    },
    [sendMessage],
  );

  const handleSendMessage = useCallback(() => {
    const trimmedInput = inputValue.trim();
    if (!trimmedInput || isConnecting) return;

    const messageHandler = userInputRequired
      ? handleUserInputResponse
      : sendMessage;

    messageHandler(trimmedInput);
    setInputValue("");
  }, [
    inputValue,
    isConnecting,
    userInputRequired,
    handleUserInputResponse,
    sendMessage,
  ]);

  // Optimized component icon mapping
  const componentIcons = useMemo(
    () => ({
      [COMPONENT_TYPE.REPORT]: <FileText size={16} className="text-blue-600" />,
      [COMPONENT_TYPE.CHART]: (
        <BarChart3 size={16} className="text-green-600" />
      ),
      [COMPONENT_TYPE.TABLE]: <Table size={16} className="text-purple-600" />,
      [COMPONENT_TYPE.ANALYSIS]: (
        <Brain size={16} className="text-orange-600" />
      ),
    }),
    [],
  );

  // Optimized component renderer
  const renderComponent = useCallback(
    (component: GeneratedComponent) => {
      const icon = componentIcons[component.type] || (
        <FileText size={16} className="text-gray-600" />
      );

      return (
        <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3">
          <div className="mb-2 flex items-center gap-2">
            {icon}
            <span className="font-medium text-blue-900 text-sm capitalize">
              {component.type} Generated
            </span>
          </div>
          <div className="rounded bg-white p-3 text-gray-800 text-sm">
            <pre className="whitespace-pre-wrap font-mono text-xs">
              {component.content}
            </pre>
          </div>
        </div>
      );
    },
    [componentIcons],
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const agent = agentData[agentId ?? ""];
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
        {messages.length === 0 ? (
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

              {/* User input required prompt */}
              {userInputRequired && (
                <div className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
                  <AlertTriangle size={16} className="text-yellow-600" />
                  <span>{userInputRequired}</span>
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            {/* Chat messages */}
            <div className="flex-1 space-y-6 overflow-y-auto p-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-4",
                    message.type === MESSAGE_TYPE.USER
                      ? "justify-end"
                      : "justify-start",
                  )}
                >
                  {(message.type === MESSAGE_TYPE.ASSISTANT ||
                    message.type === MESSAGE_TYPE.COMPONENT ||
                    message.type === MESSAGE_TYPE.ERROR) && (
                    <div className="size-8 flex-shrink-0">
                      <div
                        className={cn(
                          "flex size-8 items-center justify-center rounded-full",
                          message.type === MESSAGE_TYPE.ERROR
                            ? "bg-gradient-to-br from-red-500 to-red-600"
                            : "bg-gradient-to-br from-blue-500 to-purple-600",
                        )}
                      >
                        {message.type === MESSAGE_TYPE.ERROR ? (
                          <AlertTriangle size={16} className="text-white" />
                        ) : (
                          <Bot size={16} className="text-white" />
                        )}
                      </div>
                    </div>
                  )}

                  <div
                    className={cn(
                      "max-w-[80%] rounded-2xl px-4 py-3",
                      message.type === MESSAGE_TYPE.USER
                        ? "ml-auto bg-blue-600 text-white"
                        : message.type === MESSAGE_TYPE.ERROR
                          ? "bg-red-100 text-red-900"
                          : "bg-gray-100 text-gray-900",
                    )}
                  >
                    {/* Message content */}
                    {message.type !== MESSAGE_TYPE.COMPONENT && (
                      <div className="whitespace-pre-wrap break-words">
                        {message.content}
                        {!message.isComplete &&
                          message.type === MESSAGE_TYPE.ASSISTANT && (
                            <span className="ml-1 inline-block h-5 w-2 animate-pulse bg-gray-400" />
                          )}
                      </div>
                    )}

                    {/* Generated component */}
                    {message.component && renderComponent(message.component)}

                    {/* Tool calls */}
                    {message.toolCalls && message.toolCalls.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {message.toolCalls.map((toolCall) => (
                          <div
                            key={toolCall.id}
                            className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 p-2"
                          >
                            {toolCall.status === TOOL_CALL_STATUS.STARTED ? (
                              <Clock
                                size={14}
                                className="animate-pulse text-blue-600"
                              />
                            ) : (
                              <CheckCircle
                                size={14}
                                className="text-green-600"
                              />
                            )}
                            <span className="font-medium text-blue-900 text-sm">
                              {toolCall.name}
                            </span>
                            {toolCall.status === TOOL_CALL_STATUS.STARTED && (
                              <span className="text-blue-600 text-xs">
                                Running...
                              </span>
                            )}
                            {toolCall.result && (
                              <span className="truncate text-gray-600 text-xs">
                                {toolCall.result.substring(0, 50)}...
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Reasoning */}
                    {message.reasoning && (
                      <div className="mt-3 rounded-lg border border-yellow-200 bg-yellow-50 p-2">
                        <div className="mb-1 flex items-center gap-2">
                          <Zap size={14} className="text-yellow-600" />
                          <span className="font-medium text-sm text-yellow-900">
                            Reasoning
                          </span>
                        </div>
                        <p className="text-sm text-yellow-800">
                          {message.reasoning}
                        </p>
                      </div>
                    )}
                  </div>

                  {message.type === MESSAGE_TYPE.USER && (
                    <div className="size-8 flex-shrink-0">
                      <div className="flex size-8 items-center justify-center rounded-full bg-gray-600">
                        <User size={16} className="text-white" />
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Streaming indicator */}
              {isStreaming && (
                <div className="flex items-center gap-2 text-gray-500 text-sm">
                  <div className="flex space-x-1">
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: "0ms" }}
                    />
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: "150ms" }}
                    />
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: "300ms" }}
                    />
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
                  placeholder={
                    userInputRequired
                      ? "Agent is waiting for your response..."
                      : "Type your message..."
                  }
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

              {/* Status indicators */}
              <div className="mt-2 flex items-center justify-between text-gray-500 text-xs">
                <div className="flex items-center gap-4">
                  <span
                    className={cn(
                      "flex items-center gap-1",
                      isStreaming
                        ? "text-green-600"
                        : userInputRequired
                          ? "text-yellow-600"
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
                          : userInputRequired
                            ? "animate-pulse bg-yellow-500"
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
                        : userInputRequired
                          ? "Waiting for input"
                          : isConnecting
                            ? "Connecting"
                            : isConnected
                              ? "Ready"
                              : "Disconnected"}
                    </span>
                  </span>
                  {conversationId && <span>Session: {conversationId}</span>}
                  {currentThreadId && <span>Thread: {currentThreadId}</span>}
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
