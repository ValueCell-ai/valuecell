import { parse } from "best-effort-json-parser";
import { ChevronDown, Search } from "lucide-react";
import { type FC, memo, useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { ToolCallRendererProps } from "@/types/renderer";
import MarkdownRenderer from "./markdown-renderer";

const ToolCallRenderer: FC<ToolCallRendererProps> = ({ content }) => {
  const [isOpen, setIsOpen] = useState(false);
  const { tool_name, tool_result } = parse(content);
  const tool_result_array = parse(tool_result);

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn("min-w-96 rounded-lg border-gradient p-3")}
      data-active={isOpen}
    >
      <CollapsibleTrigger
        className={cn(
          "flex w-full items-center justify-between",
          tool_result && "cursor-pointer",
        )}
        disabled={!tool_result}
      >
        <div className="flex items-center gap-2 text-gray-950">
          {tool_result ? (
            <Search className="size-5" />
          ) : (
            <Spinner className="size-5" />
          )}
          <p className="text-base leading-5">{tool_name}</p>
        </div>
        {tool_result_array && (
          <ChevronDown
            className={cn(
              "h-6 w-6 text-gray-950 transition-transform",
              isOpen && "rotate-180",
            )}
          />
        )}
      </CollapsibleTrigger>

      {/* Collapsible Content */}
      <CollapsibleContent>
        <div className="flex flex-col gap-4 pt-2">
          {tool_result_array &&
            Array.isArray(tool_result_array) &&
            // TODO: temporarily use content as result type, need to improve later
            // biome-ignore lint/suspicious/noExplicitAny: temporarily use any as result type
            tool_result_array?.map((tool_result: any) => {
              return tool_result.content ? (
                <MarkdownRenderer
                  content={tool_result.content}
                  key={tool_result.content}
                />
              ) : (
                <p key={tool_result}>${String(tool_result)}</p>
              );
            })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};

export default memo(ToolCallRenderer);
