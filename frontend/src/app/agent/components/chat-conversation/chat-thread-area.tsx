import { type FC, Fragment, memo } from "react";
import { useStickToBottom } from "use-stick-to-bottom";
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
  const { scrollRef, contentRef } = useStickToBottom();

  return (
    <div
      ref={scrollRef}
      className={cn("scroll-container w-full flex-1 space-y-6 py-6", className)}
    >
      <main ref={contentRef} className="main-chat-area mx-auto space-y-6">
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
