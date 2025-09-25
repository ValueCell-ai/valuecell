import { ArrowUp } from "lucide-react";
import { type FC, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import ScrollTextarea from "@/components/valuecell/scroll/scroll-textarea";
import { cn } from "@/lib/utils";
import type { ConversationView } from "@/types/agent";
import ChatBackground from "./chat-background";
import ChatItemView from "./chat-item-view";

interface ChatConversationViewProps {
  currentConversation: ConversationView | null;
  isStreaming: boolean;
  sendMessage: (message: string) => Promise<void>;
}

const ChatConversationView: FC<ChatConversationViewProps> = ({
  currentConversation,
  isStreaming,
  sendMessage,
}) => {
  console.log("🚀 ~ ChatConversationView ~ isStreaming:", isStreaming);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [inputValue, setInputValue] = useState<string>("");

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send message on Enter key (excluding Shift+Enter line breaks and IME composition state)
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      await handleSendMessage();
    }
  };

  const handleSendMessage = async () => {
    setIsLoading(true);
    await sendMessage(inputValue);
    setInputValue("");
  };

  useEffect(() => {
    setIsLoading(isStreaming);
  }, [isStreaming]);

  const threads = currentConversation?.threads;

  return !threads || Object.keys(threads).length === 0 ? (
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
            value={inputValue}
            onInput={(e) => setInputValue(e.currentTarget.value)}
            onKeyDown={handleKeyDown}
            placeholder="You can inquire and analyze the trend of NVIDIA in the next three months"
            maxHeight={120}
            minHeight={24}
            disabled={isLoading}
          />
          <Button
            size="icon"
            className="size-8 cursor-pointer self-end rounded-full"
            onClick={handleSendMessage}
            disabled={isLoading}
          >
            <ArrowUp size={16} className="text-white" />
          </Button>
        </div>
      </div>
    </>
  ) : (
    <div className="flex flex-1 overflow-hidden">
      <section className="flex flex-1 flex-col">
        {/* Chat messages using original data structure */}
        <ScrollContainer className="flex-1 space-y-6 p-6">
          {currentConversation &&
            Object.entries(currentConversation.threads).map(
              ([threadId, thread], threadIndex) => {
                const threadCount = Object.keys(
                  currentConversation.threads,
                ).length;
                const showThreadSeparator = threadIndex > 0 && threadCount > 1;

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
                        return <ChatItemView key={taskId} items={task.items} />;
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
              value={inputValue}
              onInput={(e) => setInputValue(e.currentTarget.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              maxHeight={120}
              minHeight={24}
              disabled={isLoading}
            />
            <Button
              size="icon"
              className="size-8 cursor-pointer self-end rounded-full"
              onClick={handleSendMessage}
              disabled={isLoading}
            >
              <ArrowUp size={16} className="text-white" />
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default ChatConversationView;
