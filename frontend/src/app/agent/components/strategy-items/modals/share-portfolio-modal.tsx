import { downloadDir, join } from "@tauri-apps/api/path";
import { save } from "@tauri-apps/plugin-dialog";
import { openPath } from "@tauri-apps/plugin-opener";
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
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
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

      const arrayBuffer = await (
        await capture.toBlob({
          type: "png",
        })
      ).arrayBuffer();

      const filename = `valuecell-${Date.now()}.png`;
      const downloadPath = await downloadDir();
      const defaultPath = await join(downloadPath, filename);
      const path = await save({
        defaultPath,
        filters: [
          {
            name: "Image",
            extensions: ["png"],
          },
        ],
      });

      if (!path) return;

      const { writeFile } = await import("@tauri-apps/plugin-fs");
      await writeFile(path, new Uint8Array(arrayBuffer));

      setOpen(false);
      toast.success(t("sharePortfolio.toast.downloaded"), {
        action: {
          label: t("sharePortfolio.toast.openFile"),
          onClick: async () => {
            return await openPath(path);
          },
        },
      });
    } catch (err) {
      toast.error(
        t("sharePortfolio.toast.downloadFailed", {
          error: JSON.stringify(err),
        }),
        { duration: 6 * 1000 },
      );
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
        <DialogTitle className="sr-only">
          {t("sharePortfolio.title")}
        </DialogTitle>

        {/* Card to be captured */}
        <div
          ref={cardRef}
          className="relative space-y-10 overflow-hidden rounded-2xl border p-8"
          style={{
            borderColor: "rgba(0, 0, 0, 0.1)",
            color: "#111827",
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
            <p
              className="font-medium text-sm"
              style={{ color: "rgba(0, 0, 0, 0.3)" }}
            >
              {TimeUtils.now().format(TIME_FORMATS.DATETIME)}
            </p>
          </div>

          {/* Main Return */}
          <div className="space-y-4 text-center">
            <div className="font-normal text-xl">
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
          <div className="grid grid-cols-[auto_1fr] gap-y-2 text-nowrap text-sm [&>span]:text-right">
            <p>P&L</p>
            <span style={{ color: stockColors[getChangeType(data.total_pnl)] }}>
              {formatChange(data.total_pnl, "", 2)}
            </span>

            <p>{t("sharePortfolio.fields.model")}</p>
            <span>{data.llm_model_id}</span>

            <p>{t("sharePortfolio.fields.exchange")}</p>
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

            <p>{t("sharePortfolio.fields.strategy")}</p>
            <span>{data.strategy_type}</span>
          </div>

          <div
            className="flex items-center justify-between rounded-2xl border p-4 shadow-[0,4px,20px,0,rgba(113,113,113,0.08)] backdrop-blur-sm"
            style={{
              borderColor: "rgba(255, 255, 255, 0.6)",
              backgroundColor: "rgba(255, 255, 255, 0.2)",
            }}
          >
            <div className="space-y-1">
              <div
                className="font-medium text-sm"
                style={{ color: "rgba(0, 0, 0, 0.3)" }}
              >
                Publisher
              </div>
              <span className="font-normal text-base">{name}</span>
            </div>

            <div
              className="font-medium text-sm"
              style={{ color: "rgba(0, 0, 0, 0.3)" }}
            >
              ValueCell.ai
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex gap-4">
          <Button
            variant="outline"
            className="h-12 flex-1 rounded-xl border-border bg-card font-medium text-base hover:bg-muted"
            onClick={() => setOpen(false)}
          >
            {t("strategy.action.cancel")}
          </Button>

          <Button
            className="h-12 flex-1 rounded-xl bg-primary font-medium text-base text-primary-foreground hover:bg-primary/90"
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <Spinner className="mr-2 size-5" />
            ) : (
              <Download className="mr-2 size-5" />
            )}
            {t("sharePortfolio.action.download")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default memo(SharePortfolioModal);
