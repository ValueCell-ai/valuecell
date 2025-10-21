import { type FC, memo, useState } from "react";
import BackButton from "@/components/valuecell/button/back-button";
import { MarkdownRenderer } from "@/components/valuecell/renderer";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { COMPONENT_RENDERER_MAP } from "@/constants/agent";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import type { ChatItem, SectionComponentType } from "@/types/agent";

// define different component types and their specific rendering components
const SecFeedComponent: FC<{ items: ChatItem[] }> = ({ items }) => {
  const [selectedItemContent, setSelectedItemContent] = useState<string>("");
  const Component = COMPONENT_RENDERER_MAP.sec_feed;

  return selectedItemContent ? (
    <section className="flex flex-1 flex-col">
      <BackButton className="mb-3" onClick={() => setSelectedItemContent("")} />
      <MarkdownRenderer content={selectedItemContent} />
    </section>
  ) : (
    <section className="flex flex-1 flex-col">
      <h4 className="mb-3 px-4 font-medium text-lg">
        {TimeUtils.nowUTC().format(TIME_FORMATS.DATE)}
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
                    onOpen={(data) => setSelectedItemContent(data)}
                  />
                ),
            )}
          </div>
        )}
      </ScrollContainer>
    </section>
  );
};

const ModelTradeComponent: FC<{ items: ChatItem[] }> = ({ items }) => {
  const Component = COMPONENT_RENDERER_MAP.filtered_line_chart;
  return (
    <ScrollContainer className="min-w-[540px] flex-1 px-4">
      {items.length > 0 && (
        <div className="h-full space-y-3 p-4">
          {items.map(
            (item) =>
              item.payload && (
                <Component key={item.item_id} content={item.payload.content} />
              ),
          )}
        </div>
      )}
    </ScrollContainer>
  );
};

const ModelTradeTableComponent: FC<{ items: ChatItem[] }> = ({ items }) => {
  const Component = COMPONENT_RENDERER_MAP.filtered_card_push_notification;
  return (
    <ScrollContainer className="w-[404px] shrink-0 overflow-hidden px-4">
      {items.length > 0 && (
        <div className="space-y-3">
          {items.map(
            (item) =>
              item.payload && (
                <Component key={item.item_id} content={item.payload.content} />
              ),
          )}
        </div>
      )}
    </ScrollContainer>
  );
};

// component mapping table
const SECTION_COMPONENT_MAP: Record<
  SectionComponentType,
  FC<{ items: ChatItem[] }>
> = {
  sec_feed: SecFeedComponent,
  filtered_line_chart: ModelTradeComponent,
  filtered_card_push_notification: ModelTradeTableComponent,
};

interface ChatSectionComponentProps {
  componentType: SectionComponentType;
  items: ChatItem[];
}

/**
 * dynamic component renderer
 * @description dynamically select the appropriate component to render based on componentType
 */
const ChatSectionComponent: FC<ChatSectionComponentProps> = ({
  componentType,
  items,
}) => {
  const Component = SECTION_COMPONENT_MAP[componentType];

  return <Component items={items} />;
};

export default memo(ChatSectionComponent);
