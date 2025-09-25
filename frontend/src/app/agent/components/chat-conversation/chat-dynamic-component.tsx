import { type FC, memo } from "react";
import type { ChatItem, SectionComponentType } from "@/types/agent";
import ChatItemArea from "./chat-item-area";

// define different component types and their specific rendering components
const SecFeatureComponent: FC<{ items: ChatItem[] }> = ({ items }) => (
  <div className="space-y-4">
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <h4 className="mb-3 font-medium text-blue-900 text-sm">✨ Features</h4>
      <ChatItemArea items={items} />
    </div>
  </div>
);

const SecProfileComponent: FC<{ items: ChatItem[] }> = ({ items }) => (
  <div className="space-y-4">
    <div className="rounded-lg border border-green-200 bg-green-50 p-4">
      <h4 className="mb-3 font-medium text-green-900 text-sm">👤 Profile</h4>
      <ChatItemArea items={items} />
    </div>
  </div>
);

const SecChartComponent: FC<{ items: ChatItem[] }> = ({ items }) => (
  <div className="space-y-4">
    <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
      <h4 className="mb-3 font-medium text-purple-900 text-sm">📊 Charts</h4>
      <ChatItemArea items={items} />
    </div>
  </div>
);

const SecNewsComponent: FC<{ items: ChatItem[] }> = ({ items }) => (
  <div className="space-y-4">
    <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
      <h4 className="mb-3 font-medium text-orange-900 text-sm">📰 News</h4>
      <ChatItemArea items={items} />
    </div>
  </div>
);

// component mapping table
const COMPONENT_MAP: Record<SectionComponentType, FC<{ items: ChatItem[] }>> = {
  "sec-feature": SecFeatureComponent,
  "sec-profile": SecProfileComponent,
  "sec-chart": SecChartComponent,
  "sec-news": SecNewsComponent,
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
