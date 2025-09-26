import { type FC, memo } from "react";
import type { ChatItem, SectionComponentType } from "@/types/agent";
import ChatItemArea from "./chat-item-area";

// define different component types and their specific rendering components

const SecFeedComponent: FC<{ items: ChatItem[] }> = ({ items }) => (
  <div className="space-y-4">
    <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
      <h4 className="mb-3 font-medium text-orange-900 text-sm">📰 News</h4>
      <ChatItemArea items={items} />
    </div>
  </div>
);

// component mapping table
const COMPONENT_MAP: Record<SectionComponentType, FC<{ items: ChatItem[] }>> = {
  sec_feed: SecFeedComponent,
};

interface ChatDynamicComponentProps {
  componentType: SectionComponentType;
  items: ChatItem[];
}

/**
 * dynamic component renderer
 * @description dynamically select the appropriate component to render based on componentType
 */
const ChatDynamicComponent: FC<ChatDynamicComponentProps> = ({
  componentType,
  items,
}) => {
  const Component = COMPONENT_MAP[componentType];

  return <Component items={items} />;
};

export default memo(ChatDynamicComponent);
