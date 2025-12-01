import { Brain, ChevronDown } from "lucide-react";
import { type FC, memo, useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { ReasoningRendererProps } from "@/types/renderer";
import MarkdownRenderer from "./markdown-renderer";

const ReasoningRenderer: FC<ReasoningRendererProps> = ({
  content,
  isComplete,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const hasContent = content && content.trim().length > 0;

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
          hasContent && "cursor-pointer",
        )}
        disabled={!hasContent}
      >
        <div className="flex items-center gap-2 text-gray-950">
          {isComplete ? (
            <Brain className="size-5" />
          ) : (
            <Spinner className="size-5" />
          )}
          <p className="text-base leading-5">
            {isComplete ? "Thinking" : "Thinking..."}
          </p>
        </div>
        {hasContent && (
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
        <div className="pt-2">
          {hasContent && (
            <MarkdownRenderer
              content={content}
              className="text-gray-600 text-xs"
            />
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};

export default memo(ReasoningRenderer);
