import { snapdom } from "@zumer/snapdom";
import { Download } from "lucide-react";
import {
  type FC,
  memo,
  type RefObject,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { PngIcon, RoundedLogo } from "@/components/valuecell/icon";
import { EXCHANGE_ICONS } from "@/constants/icons";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { formatChange, getChangeType } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import { useSystemInfo } from "@/store/system-store";
import type { StrategyPerformance } from "@/types/strategy";

type SharePortfolioData = Pick<
  StrategyPerformance,
  "return_rate_pct" | "llm_model_id" | "exchange_id" | "strategy_type"
> & {
  total_pnl: number;
  created_at: string;
};

export interface SharePortfolioCardRef {
  open: (data: SharePortfolioData) => Promise<void> | void;
}

const SharePortfolioModal: FC<{
  ref?: RefObject<SharePortfolioCardRef | null>;
}> = ({ ref }) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const [open, setOpen] = useState(false);
  const [data, setData] = useState<SharePortfolioData | null>(null);

  const stockColors = useStockColors();
  const { name } = useSystemInfo();

  const handleDownload = async () => {
    if (!cardRef.current) return;

    try {
      setIsDownloading(true);
      const capture = await snapdom(cardRef.current, {
        scale: 2,
        outerTransforms: true,
        outerShadows: true,
        backgroundColor: "#ffffff",
      });

      await capture.download({
        filename: `valuecell-${Date.now()}`,
        type: "png",
      });

      setOpen(false);
      toast.success("Image downloaded in your Downloads folder");
    } catch (err) {
      toast.error(`Failed to download image: ${JSON.stringify(err)}`);
    } finally {
      setIsDownloading(false);
    }
  };

  useImperativeHandle(ref, () => ({
    open: (data: SharePortfolioData) => {
      setData(data);
      setOpen(true);
    },
  }));

  if (!data) return null;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="h-[600px] w-[434px] overflow-hidden border-none bg-transparent p-0 shadow-none"
        showCloseButton={false}
      >
        <DialogTitle className="sr-only">Share Portfolio</DialogTitle>

        {/* Card to be captured */}
        <div
          ref={cardRef}
          className="relative space-y-10 overflow-hidden rounded-2xl border border-gray-200 p-8"
          style={{
            background:
              "linear-gradient(141deg, rgba(255, 255, 255, 0.32) 2.67%, rgba(255, 255, 255, 0.00) 48.22%), radial-gradient(109.08% 168.86% at 54.34% 8.71%, #FFF 0%, #FFF 37.09%, rgba(255, 255, 255, 0.30) 94.85%, rgba(0, 0, 0, 0.00) 100%), linear-gradient(90deg, rgba(255, 36, 61, 0.85) 0.01%, rgba(0, 99, 246, 0.85) 99.77%), #FFF",
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RoundedLogo />
              <span className="font-semibold text-2xl tracking-tight">
                ValueCell
              </span>
            </div>
            <p className="font-medium text-black/30 text-sm">
              {TimeUtils.now().format(TIME_FORMATS.DATETIME)}
            </p>
          </div>

          {/* Main Return */}
          <div className="space-y-4 text-center">
            <div className="font-normal text-gray-950 text-xl">
              {TimeUtils.formUTCDiff(data.created_at)}-Day ROI
            </div>
            <div
              className="font-bold text-6xl tracking-tighter"
              style={{
                color: stockColors[getChangeType(data.return_rate_pct)],
              }}
            >
              {formatChange(data.return_rate_pct, "%", 2)}
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-[auto_1fr] gap-y-2 text-nowrap text-gray-950 text-sm [&>span]:text-right">
            <p>P&L</p>
            <span style={{ color: stockColors[getChangeType(data.total_pnl)] }}>
              {formatChange(data.total_pnl, "", 2)}
            </span>

            <p>Model</p>
            <span>{data.llm_model_id}</span>

            <p>Exchange</p>
            <span className="ml-auto flex items-center gap-1">
              <PngIcon
                src={
                  EXCHANGE_ICONS[
                    data.exchange_id as keyof typeof EXCHANGE_ICONS
                  ]
                }
                className="size-4"
              />
              {data.exchange_id}
            </span>

            <p>Strategy</p>
            <span>{data.strategy_type}</span>
          </div>

          <div className="flex items-center justify-between rounded-2xl border border-white/60 bg-white/20 p-4 shadow-[0,4px,20px,0,rgba(113,113,113,0.08)] backdrop-blur-sm">
            <div className="space-y-1">
              <div className="font-medium text-black/30 text-sm">Publisher</div>
              <span className="font-normal text-base text-gray-950">
                {name}
              </span>
            </div>

            <div className="font-medium text-black/30 text-sm">
              ValueCell.ai
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex gap-4">
          <Button
            variant="outline"
            className="h-12 flex-1 rounded-xl border-gray-200 bg-white font-medium text-base hover:bg-gray-50"
            onClick={() => setOpen(false)}
          >
            Cancel
          </Button>

          <Button
            className="h-12 flex-1 rounded-xl bg-gray-950 font-medium text-base text-white hover:bg-gray-800"
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <Spinner className="mr-2 size-5" />
            ) : (
              <Download className="mr-2 size-5" />
            )}
            Download
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default memo(SharePortfolioModal);
