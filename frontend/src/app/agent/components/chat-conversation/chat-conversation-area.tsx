import { type FC, memo, useCallback, useState } from "react";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import {
  MultiSectionProvider,
  useMultiSection,
} from "@/provider/multi-section-provider";
import type {
  AgentInfo,
  ConversationView,
  MultiSectionComponentType,
  SectionComponentType,
} from "@/types/agent";
import ChatConversationHeader from "./chat-conversation-header";
import ChatInputArea from "./chat-input-area";
import ChatMultiSectionComponent from "./chat-multi-section-component";
import ChatSectionComponent from "./chat-section-component";
import ChatThreadArea from "./chat-thread-area";
import ChatWelcomeScreen from "./chat-welcome-screen";

interface ChatConversationAreaProps {
  agent: AgentInfo;
  currentConversation: ConversationView | null;
  isStreaming: boolean;
  sendMessage: (message: string) => Promise<void>;
}

const ChatConversationAreaContent: FC<ChatConversationAreaProps> = ({
  agent,
  currentConversation,
  isStreaming,
  sendMessage,
}) => {
  const [inputValue, setInputValue] = useState<string>("");
  const { currentSection } = useMultiSection();

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
      <>
        <ChatConversationHeader agent={agent} />
        <ChatWelcomeScreen
          title={`Welcome to ${agent.display_name}!`}
          inputValue={inputValue}
          onInputChange={handleInputChange}
          onSendMessage={handleSendMessage}
          disabled={isStreaming}
        />
      </>
    );
  }

  return (
    <div className="flex flex-1 gap-2 overflow-hidden">
      {/* main section */}
      <section className="flex flex-1 flex-col items-center">
        <ChatConversationHeader agent={agent} />

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

      {/* Chat section components: one section per special component_type */}
      {currentConversation.sections &&
        Object.entries(currentConversation.sections).map(
          ([componentType, items]) => (
            <ChatSectionComponent
              key={componentType}
              // TODO: componentType as type assertion is not safe, find a better way to do this
              componentType={componentType as SectionComponentType}
              items={items}
            />
          ),
        )}

      {/* Multi-section detail view */}
      {currentSection && (
        <section className="flex flex-1 flex-col py-4">
          <ScrollContainer>
            <ChatMultiSectionComponent
              componentType={
                // only the component_type is the same as the MultiSectionComponentType
                currentSection.component_type as MultiSectionComponentType
              }
              content={currentSection.payload.content}
            />
          </ScrollContainer>
        </section>
      )}
    </div>
  );
};

const ChatConversationArea: FC<ChatConversationAreaProps> = (props) => {
  return (
    <MultiSectionProvider>
      <ChatConversationAreaContent {...props} />
    </MultiSectionProvider>
  );
};

export default memo(ChatConversationArea);
