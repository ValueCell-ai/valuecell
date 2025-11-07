import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { ScheduledTaskRendererProps } from "@/types/renderer";

const ScheduledTaskRenderer: FC<ScheduledTaskRendererProps> = ({
  content,
  onOpen,
}) => {
  const { result, create_time } = parse(content);

  return (
    <div
      className={cn(
        "group relative flex h-full cursor-pointer flex-col gap-3 rounded-lg border-gradient bg-gray-50 p-4 text-gray-950 transition-all",
      )}
      onClick={() => onOpen?.(result)}
    >
      <p className="whitespace-nowrap text-gray-400 text-sm">
        {TimeUtils.formatUTC(create_time, TIME_FORMATS.DATETIME_SHORT)}
      </p>
      {/* content */}
      <div className="relative z-10 line-clamp-2 w-full">{result}</div>
    </div>
  );
};

export default memo(ScheduledTaskRenderer);
