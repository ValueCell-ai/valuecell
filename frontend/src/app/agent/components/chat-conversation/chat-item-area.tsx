import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import { UnknownRenderer } from "@/components/valuecell/renderer";
import { COMPONENT_RENDERER_MAP } from "@/constants/agent";
import { cn } from "@/lib/utils";
import { useMultiSection } from "@/provider/multi-section-provider";
import type { ChatItem } from "@/types/agent";

export interface ChatItemAreaProps {
  items: ChatItem[];
}

const ChatItemArea: FC<ChatItemAreaProps> = ({ items }) => {
  const { currentSection, openSection } = useMultiSection();

  // If no items, don't render anything
  if (!items || items.length === 0) return null;

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div
          key={item.item_id}
          className={cn(
            "flex gap-4",
            item.role === "user" ? "justify-end" : "justify-start",
          )}
        >
          <div
            id="chat-item"
            className={cn("max-w-[80%] rounded-2xl px-4", {
              "ml-auto bg-gray-50 py-2.5": item.role === "user",
            })}
          >
            {/* Render different message types based on payload structure */}
            {(() => {
              const RendererComponent =
                COMPONENT_RENDERER_MAP[item.component_type];

              if (!item.payload) return null;
              switch (item.component_type) {
                case "markdown":
                case "tool_call":
                case "subagent_conversation":
                case "scheduled_task_controller":
                  return <RendererComponent content={item.payload.content} />;

                case "reasoning": {
                  const parsed = parse(item.payload.content);
                  return (
                    <RendererComponent
                      content={parsed?.content ?? ""}
                      isComplete={parsed?.isComplete ?? false}
                    />
                  );
                }

                case "report":
                  return (
                    <RendererComponent
                      content={item.payload.content}
                      onOpen={() => openSection(item)}
                      isActive={currentSection?.item_id === item.item_id}
                    />
                  );

                default:
                  return (
                    <UnknownRenderer
                      item={item}
                      content={item.payload.content}
                    />
                  );
              }
            })()}
          </div>
        </div>
      ))}
    </div>
  );
};

export default memo(ChatItemArea);
