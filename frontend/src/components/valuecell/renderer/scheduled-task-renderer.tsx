import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { ScheduledTaskRendererProps } from "@/types/renderer";
import styles from "./index.module.css";
import MarkdownRenderer from "./markdown-renderer";

const ScheduledTaskRenderer: FC<ScheduledTaskRendererProps> = ({
  content,
  onOpen,
}) => {
  const { result, create_time } = parse(content);

  return (
    <div
      className={cn(
        "group relative flex h-full cursor-pointer flex-col gap-3 rounded-2xl bg-gray-50 p-4 transition-all",
        styles["border-gradient"],
      )}
      onClick={() => onOpen?.(result)}
    >
      {/* content */}
      <div className="relative z-10 max-h-24 w-full overflow-hidden">
        <MarkdownRenderer content={result} />
      </div>

      <p className="whitespace-nowrap text-right text-gray-400 text-xs">
        {TimeUtils.fromUTC(create_time).format(TIME_FORMATS.DATETIME_SHORT)}
      </p>
    </div>
  );
};

export default memo(ScheduledTaskRenderer);
