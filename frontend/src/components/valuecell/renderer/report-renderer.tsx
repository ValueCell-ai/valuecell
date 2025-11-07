import { parse } from "best-effort-json-parser";
import { ChevronRight, FileText } from "lucide-react";
import { type FC, memo } from "react";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { cn } from "@/lib/utils";
import type { ReportRendererProps } from "@/types/renderer";

const ReportRenderer: FC<ReportRendererProps> = ({
  content,
  onOpen,
  isActive,
}) => {
  const { title, create_time, data } = parse(content);

  return (
    <div
      data-active={isActive}
      className={cn(
        "flex h-full min-w-96 items-center justify-between gap-2 rounded-xl px-4 py-5",
        "cursor-pointer border-gradient transition-all duration-200",
      )}
      onClick={() => onOpen?.(data)}
    >
      {/* Left side: Icon and text */}
      <div className="flex items-center gap-2">
        {/* Document icon with background */}
        <div className="flex size-10 items-center justify-center rounded-xl bg-linear-to-br from-5% from-[#3A88FF] to-80% to-[#FF6699]">
          <FileText className="size-6 text-white" />
        </div>

        {/* Text content */}
        <div className="flex flex-col gap-1">
          <p className="font-normal text-base text-gray-950 leading-5">
            {title}
          </p>
          <p className="whitespace-nowrap text-gray-400 text-xs leading-4">
            {`Created at: ${TimeUtils.formatUTC(create_time, TIME_FORMATS.DATE)}`}
          </p>
        </div>
      </div>

      {/* Right side: Arrow icon */}
      <ChevronRight className="size-6 text-gray-700" />
    </div>
  );
};

export default memo(ReportRenderer);
