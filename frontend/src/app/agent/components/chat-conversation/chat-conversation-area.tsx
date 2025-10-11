import { type FC, memo, useCallback, useState } from "react";
import type { ConversationView, SectionComponentType } from "@/types/agent";
import ChatDynamicComponent from "./chat-dynamic-component";
import ChatInputArea from "./chat-input-area";
import ChatThreadArea from "./chat-thread-area";
import ChatWelcomeScreen from "./chat-welcome-screen";

interface ChatConversationAreaProps {
  displayName: string;
  currentConversation: ConversationView | null;
  isStreaming: boolean;
  sendMessage: (message: string) => Promise<void>;
}

const ChatConversationArea: FC<ChatConversationAreaProps> = ({
  displayName,
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
        title={`Welcome to ${displayName}!`}
        inputValue={inputValue}
        onInputChange={handleInputChange}
        onSendMessage={handleSendMessage}
        disabled={isStreaming}
      />
    );
  }

  return (
    <div className="flex flex-1 gap-2 overflow-hidden">
      {/* main section */}
      <section className="flex flex-1 flex-col items-center">
        <ChatThreadArea
          threads={currentConversation.threads}
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

      {/* Dynamic sections: one section per special component_type */}
      {currentConversation.sections &&
        Object.entries(currentConversation.sections).map(
          ([componentType, items]) => (
            <section key={componentType} className="flex flex-1 flex-col py-4">
              {/* Section content using dynamic component rendering */}
              <ChatDynamicComponent
                // TODO: componentType as type assertion is not safe, find a better way to do this
                componentType={componentType as SectionComponentType}
                items={items}
              />
            </section>
          ),
        )}
    </div>
  );
};

export default memo(ChatConversationArea);
