import { type FC, memo, useCallback, useState } from "react";
import type { ConversationView } from "@/types/agent";
import ChatInputArea from "./chat-input-area";
import ChatThreadArea from "./chat-thread-area";
import ChatWelcomeScreen from "./chat-welcome-screen";

interface ChatConversationAreaProps {
  currentConversation: ConversationView | null;
  isStreaming: boolean;
  sendMessage: (message: string) => Promise<void>;
}

const ChatConversationArea: FC<ChatConversationAreaProps> = ({
  currentConversation,
  isStreaming,
  sendMessage,
}) => {
  const [inputValue, setInputValue] = useState<string>("");

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

  // Check if conversation has any messages
  const hasMessages =
    currentConversation?.threads &&
    Object.keys(currentConversation.threads).length > 0;

  if (!hasMessages) {
    return (
      <ChatWelcomeScreen
        inputValue={inputValue}
        onInputChange={handleInputChange}
        onSendMessage={handleSendMessage}
        disabled={isStreaming}
      />
    );
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <section className="flex flex-1 flex-col">
        {/* Chat messages using original data structure */}
        <ChatThreadArea
          conversation={currentConversation}
          isStreaming={isStreaming}
        />

        {/* Input area at bottom */}
        <div className="border-gray-200 border-t p-4">
          <ChatInputArea
            value={inputValue}
            onChange={handleInputChange}
            onSend={handleSendMessage}
            placeholder="Type your message..."
            disabled={isStreaming}
            variant="chat"
          />
        </div>
      </section>
    </div>
  );
};

export default memo(ChatConversationArea);
