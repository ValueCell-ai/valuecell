import { type FC, Fragment, memo, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { ConversationView } from "@/types/agent";
import ChatItemArea from "./chat-item-area";
import ChatStreamingIndicator from "./chat-streaming-indicator";

interface ChatThreadAreaProps {
  className?: string;
  threads: ConversationView["threads"];
  isStreaming: boolean;
}

const ChatThreadArea: FC<ChatThreadAreaProps> = ({
  className,
  threads,
  isStreaming,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const wasNearBottomRef = useRef(true);

  // Check if user is at/near bottom of scroll container
  const isNearBottom = () => {
    const el = scrollRef.current;
    if (!el) return true;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const threshold = 50;
    return scrollHeight - scrollTop - clientHeight < threshold;
  };

  // Track scroll position
  // biome-ignore lint/correctness/useExhaustiveDependencies: isNearBottom uses ref, no need to track
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const handleScroll = () => {
      wasNearBottomRef.current = isNearBottom();
    };

    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-scroll when content changes if user was near bottom
  // biome-ignore lint/correctness/useExhaustiveDependencies: threads/isStreaming trigger scroll on content change
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !wasNearBottomRef.current) return;

    el.scrollTo({
      top: el.scrollHeight,
      behavior: "smooth",
    });
  }, [threads, isStreaming]);

  return (
    <div
      ref={scrollRef}
      className={cn("scroll-container w-full flex-1 space-y-6 py-6", className)}
    >
      <main className="main-chat-area mx-auto space-y-6">
        {Object.entries(threads).map(([threadId, thread]) => {
          return (
            <Fragment key={threadId}>
              {/* Render all tasks within this thread */}
              {Object.entries(thread.tasks).map(([taskId, task]) => {
                if (task.items && task.items.length > 0) {
                  return <ChatItemArea key={taskId} items={task.items} />;
                }
                return null;
              })}
            </Fragment>
          );
        })}

        {/* Streaming indicator */}
        {isStreaming && <ChatStreamingIndicator />}
      </main>
    </div>
  );
};

export default memo(ChatThreadArea);
