import { parse } from "best-effort-json-parser";
import { type FC, memo } from "react";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { SecFeedRendererProps } from "@/types/renderer";
import styles from "./index.module.css";
import MarkdownRenderer from "./markdown-renderer";

const SecFeedRenderer: FC<SecFeedRendererProps> = ({ content, onOpen }) => {
  const { ticker, data, source, create_time } = parse(content);

  return (
    <div
      className={cn(
        "group relative flex h-full cursor-pointer flex-col gap-3 rounded-2xl bg-gray-50 p-4 transition-all",
        styles["border-gradient"],
      )}
      onClick={() => onOpen?.(data)}
    >
      {/* content */}
      <div className="relative z-10 max-h-24 w-full overflow-hidden">
        <MarkdownRenderer content={data} />
      </div>

      {/* footer info */}
      <div className="relative z-10 flex w-full items-center justify-between text-gray-400 text-xs">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-base text-gray-950">
            {ticker}
          </span>
          <span className="whitespace-nowrap">Source: {source}</span>
        </div>
        <span className="whitespace-nowrap">
          {TimeUtils.fromUTC(create_time).format(TIME_FORMATS.DATETIME_SHORT)}
        </span>
      </div>
    </div>
  );
};

export default memo(SecFeedRenderer);
