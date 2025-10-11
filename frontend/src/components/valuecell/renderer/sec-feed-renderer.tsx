import { type FC, memo } from "react";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import MarkdownRenderer from "./markdown-renderer";

interface SecFeedRendererProps {
  content: string;
  onClick?: () => void;
}

const SecFeedRenderer: FC<SecFeedRendererProps> = ({ content, onClick }) => {
  const { ticker, data, source, create_time } = JSON.parse(content);

  return (
    <div
      className="group relative flex h-full cursor-pointer flex-col gap-3 rounded-2xl bg-gray-50 p-4 transition-all duration-200 hover:shadow-sm"
      onClick={onClick}
    >
      {/* gradient border on hover */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-red-400 via-pink-300 to-pink-200 p-px opacity-0 transition-opacity duration-200 group-hover:opacity-100">
        <div className="h-full rounded-2xl bg-gray-50" />
      </div>

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
