import { Plus } from "lucide-react";
import { type FC, memo } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface TagGroupsProps {
  tags: string[];
  maxVisible?: number;
  className?: string;
  tagClassName?: string;
}

const TagGroups: FC<TagGroupsProps> = ({
  tags,
  maxVisible = 3,
  className,
  tagClassName,
}) => {
  const visibleTags = tags.slice(0, maxVisible);
  const remainingTags = tags.slice(maxVisible);
  const hasMoreTags = remainingTags.length > 0;

  return (
    <div className={cn("flex items-center gap-1", className)}>
      {visibleTags.map((tag) => (
        <span
          key={tag}
          className={cn(
            "text-nowrap rounded-md bg-gray-100 px-3 py-1 font-normal text-gray-700 text-xs",
            tagClassName,
          )}
        >
          {tag}
        </span>
      ))}

      {hasMoreTags && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="flex items-center text-nowrap rounded-md bg-gray-100 px-2 py-1 font-normal text-gray-600 text-xs transition-colors hover:bg-gray-200"
            >
              <Plus size={12} />
              <span>{remainingTags.length}</span>
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <div className="flex flex-wrap gap-1.5">
              {remainingTags.map((tag) => (
                <span
                  key={tag}
                  className="text-nowrap rounded-md bg-gray-700 px-2 py-0.5 text-white text-xs"
                >
                  {tag}
                </span>
              ))}
            </div>
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  );
};

export default memo(TagGroups);
