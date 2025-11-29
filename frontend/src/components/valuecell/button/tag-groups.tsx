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

export const Tag = ({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) => {
  return (
    <span
      className={cn(
        "flex w-fit items-center gap-2 text-nowrap rounded-md bg-gray-100 px-3 py-1 font-normal text-gray-700 text-xs",
        className,
      )}
    >
      {children}
    </span>
  );
};

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
        <Tag key={tag} className={tagClassName}>
          {tag}
        </Tag>
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
                <Tag key={tag} className="bg-gray-700 text-white">
                  {tag}
                </Tag>
              ))}
            </div>
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  );
};

export default memo(TagGroups);
