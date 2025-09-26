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
      className="group relative box-border flex size-full cursor-pointer flex-col items-start gap-[12px] rounded-[16px] bg-gray-50 p-[16px] transition-all duration-200 hover:shadow-sm"
      onClick={onClick}
    >
      {/* gradient border only show when hover */}
      <div
        className="pointer-events-none absolute inset-0 rounded-[16px] opacity-0 transition-opacity duration-200 group-hover:opacity-100"
        style={{
          background:
            "linear-gradient(135deg, #ff7080, #ff9a9e, #fecfef, #fecfef)",
          padding: "1px",
        }}
      >
        <div className="size-full rounded-[15px] bg-gray-50" />
      </div>

      {/* content area */}
      <div className="relative z-10 flex w-full shrink-0 flex-col items-start gap-[8px]">
        <div className="flex w-full shrink-0 flex-col items-start gap-[9px]">
          <MarkdownRenderer content={data} />
        </div>
      </div>

      {/* bottom info area */}
      <div className="relative z-10 flex w-full shrink-0 items-center justify-between">
        <div className="relative flex shrink-0 items-center gap-[12px]">
          <div className="relative flex shrink-0 items-center gap-[12px]">
            <div className="relative flex shrink-0 items-center gap-[4px]">
              <div className="relative flex shrink-0 items-center gap-[5px] overflow-clip rounded-[500px] bg-gray-50">
                <p className="relative w-full shrink-0 font-['PingFang_SC'] font-semibold text-[16px] text-gray-950 not-italic leading-[22px]">
                  {ticker}
                </p>
              </div>
              <p className="relative shrink-0 whitespace-pre text-nowrap font-['PingFang_SC'] font-normal text-[12px] text-gray-400 not-italic leading-[18px]">
                {source}
              </p>
            </div>

            <div className="relative flex shrink-0 items-center gap-[8px]">
              <p className="relative shrink-0 whitespace-pre text-nowrap font-['PingFang_SC'] font-normal text-[12px] text-gray-400 not-italic leading-[18px]">
                Source：{source}
              </p>
            </div>
          </div>
        </div>

        <div className="relative flex shrink-0 items-center gap-[8px]">
          <p className="relative shrink-0 whitespace-pre text-nowrap font-['PingFang_SC'] font-normal text-[12px] text-gray-400 not-italic leading-[18px]">
            {TimeUtils.fromUTC(create_time).format(TIME_FORMATS.DATETIME_SHORT)}
          </p>
        </div>
      </div>
    </div>
  );
};

export default memo(SecFeedRenderer);
