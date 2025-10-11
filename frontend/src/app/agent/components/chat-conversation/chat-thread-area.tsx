import { type FC, memo } from "react";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import type { ConversationView } from "@/types/agent";
import ChatItemArea from "./chat-item-area";
import ChatStreamingIndicator from "./chat-streaming-indicator";

interface ChatThreadAreaProps {
  threads: ConversationView["threads"];
  isStreaming: boolean;
}

const ChatThreadArea: FC<ChatThreadAreaProps> = ({ threads, isStreaming }) => {
  return (
    <ScrollContainer className="w-full flex-1 space-y-6 py-6">
      {Object.entries(threads).map(([threadId, thread]) => {
        return (
          <div key={threadId} className="space-y-6">
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
