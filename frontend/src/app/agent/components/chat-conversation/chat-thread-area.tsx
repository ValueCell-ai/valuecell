import { type FC, memo, useMemo } from "react";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import type { ConversationView } from "@/types/agent";
import ChatItemArea from "./chat-item-area";
import ChatStreamingIndicator from "./chat-streaming-indicator";

interface ChatThreadAreaProps {
  threads: ConversationView["threads"];
  isStreaming: boolean;
}

const ChatThreadArea: FC<ChatThreadAreaProps> = ({ threads, isStreaming }) => {
  // Pre-calculate thread count to avoid recomputation
  const threadCount = useMemo(() => Object.keys(threads).length, [threads]);

  return (
    <ScrollContainer className="flex-1 space-y-6 p-6">
      {Object.entries(threads).map(([threadId, thread], threadIndex) => {
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
                return <ChatItemArea key={taskId} items={task.items} />;
              }
              return null;
            })}
          </div>
        );
      })}

      {/* Streaming indicator */}
      {isStreaming && <ChatStreamingIndicator />}
    </ScrollContainer>
  );
};

export default memo(ChatThreadArea);
