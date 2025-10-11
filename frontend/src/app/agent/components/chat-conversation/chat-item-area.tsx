import { FileText } from "lucide-react";
import { type FC, memo } from "react";
import { COMPONENT_RENDERER_MAP } from "@/constants/agent";
import { cn } from "@/lib/utils";
import type { ChatItem } from "@/types/agent";

export interface ChatItemAreaProps {
  items: ChatItem[];
}

const ChatItemArea: FC<ChatItemAreaProps> = ({ items }) => {
  // If no items, don't render anything
  if (!items || items.length === 0) return null;

  return (
    <div className="main-chat-area mx-auto space-y-3">
      {items.map((item) => (
        <div
          key={item.item_id}
          className={cn(
            "flex gap-4",
            item.role === "user" ? "justify-end" : "justify-start",
          )}
        >
          <div
            className={cn("max-w-[80%] rounded-2xl px-4 py-2.5", {
              "ml-auto bg-gray-50": item.role === "user",
            })}
          >
            {/* Render different message types based on payload structure */}
            {(() => {
              if ("component_type" in item) {
                const RendererComponent =
                  COMPONENT_RENDERER_MAP[item.component_type];

                const payload = item.payload;
                if (!payload) return null;

                return RendererComponent ? (
                  <RendererComponent content={payload.content} />
                ) : (
                  <div>
                    <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3">
                      <div className="mb-2 flex items-center gap-2">
                        <FileText size={16} className="text-blue-600" />
                        <span className="font-medium text-blue-900 text-sm capitalize">
                          {item.component_type} (Unknown Component Type)
                        </span>
                      </div>
                      <div className="rounded bg-white p-3 text-gray-800 text-sm">
                        <pre className="whitespace-pre-wrap font-mono text-xs">
                          {payload.content}
                        </pre>
                      </div>
                    </div>
                  </div>
                );
              }
              return null;
            })()}
          </div>
        </div>
      ))}
    </div>
  );
};

export default memo(ChatItemArea);
