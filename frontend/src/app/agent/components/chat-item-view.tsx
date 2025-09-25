import { Bot, CheckCircle, Clock, FileText, User } from "lucide-react";
import { type FC, memo } from "react";
import { cn } from "@/lib/utils";
import type { ChatItem } from "@/types/agent";

export interface ChatItemViewProps {
  items: ChatItem[];
}

const ChatItemView: FC<ChatItemViewProps> = ({ items }) => {
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
          {item.role !== "user" && (
            <div className="size-8 flex-shrink-0">
              <div className="flex size-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600">
                <Bot size={16} className="text-white" />
              </div>
            </div>
          )}

          <div
            className={cn(
              "max-w-[80%] rounded-2xl px-4 py-3",
              item.role === "user"
                ? "ml-auto bg-blue-600 text-white"
                : "bg-gray-100 text-gray-900",
            )}
          >
            {/* Render different message types based on payload structure */}
            {(() => {
              const payload = item.payload;
              if (!payload) return null;

              // Component generator message
              if ("component_type" in payload && "content" in payload) {
                return (
                  <div>
                    <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3">
                      <div className="mb-2 flex items-center gap-2">
                        <FileText size={16} className="text-blue-600" />
                        <span className="font-medium text-blue-900 text-sm capitalize">
                          {payload.component_type} Generated
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

              // Tool call message
              if ("tool_call_id" in payload && "tool_name" in payload) {
                const hasResult =
                  "tool_call_result" in payload && payload.tool_call_result;
                return (
                  <div>
                    <div className="mt-3 flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 p-2">
                      {hasResult ? (
                        <CheckCircle size={14} className="text-green-600" />
                      ) : (
                        <Clock
                          size={14}
                          className="animate-pulse text-blue-600"
                        />
                      )}
                      <span className="font-medium text-blue-900 text-sm">
                        {payload.tool_name}
                      </span>
                      {hasResult ? (
                        <span className="truncate text-gray-600 text-xs">
                          {String(payload.tool_call_result).substring(0, 50)}
                          ...
                        </span>
                      ) : (
                        <span className="text-blue-600 text-xs">
                          Running...
                        </span>
                      )}
                    </div>
                  </div>
                );
              }

              // Regular content message
              if ("content" in payload) {
                return (
                  <div className="whitespace-pre-wrap break-words">
                    {payload.content}
                  </div>
                );
              }

              return null;
            })()}
          </div>

          {item.role === "user" && (
            <div className="size-8 flex-shrink-0">
              <div className="flex size-8 items-center justify-center rounded-full bg-gray-600">
                <User size={16} className="text-white" />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default memo(ChatItemView);
