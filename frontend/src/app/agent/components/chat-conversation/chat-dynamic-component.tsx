import { type FC, memo } from "react";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { COMPONENT_RENDERER_MAP } from "@/constants/agent";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import type { ChatItem, SectionComponentType } from "@/types/agent";

// define different component types and their specific rendering components
const SecFeedComponent: FC<{ items: ChatItem[] }> = ({ items }) => {
  const Component = COMPONENT_RENDERER_MAP.sec_feed;

  return (
    <>
      <h4 className="mb-3 px-4 font-medium text-sm">
        {TimeUtils.nowUTC().format(TIME_FORMATS.DATETIME_SHORT)}
      </h4>

      {/* render items */}
      <ScrollContainer className="flex-1 px-4">
        {items.length > 0 && (
          <div className="space-y-3">
            {items.map(
              (item) =>
                item.payload && (
                  <Component
                    key={item.item_id}
                    content={item.payload.content}
                  />
                ),
            )}
          </div>
        )}
      </ScrollContainer>
    </>
  );
};

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
