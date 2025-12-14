import { LineChart, Wallet } from "lucide-react";
import { type FC, memo, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useStrategyPerformance } from "@/api/strategy";
import { usePublishStrategy } from "@/api/system";
import { ValueCellAgentPng } from "@/assets/png";
import { Send, Share } from "@/assets/svg";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import MultiLineChart from "@/components/valuecell/charts/model-multi-line";
import { PngIcon } from "@/components/valuecell/icon/png-icon";
import SvgIcon from "@/components/valuecell/icon/svg-icon";
import LoginModal from "@/components/valuecell/modal/login-modal";
import { useTauriInfo } from "@/hooks/use-tauri-info";
import {
  formatChange,
  getChangeType,
  getCoinCapIcon,
  numberFixed,
} from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import { useIsLoggedIn, useSystemInfo } from "@/store/system-store";
import type { PortfolioSummary, Position, Strategy } from "@/types/strategy";
import type { SharePortfolioCardRef } from "./modals/share-portfolio-modal";
import SharePortfolioModal from "./modals/share-portfolio-modal";

interface PortfolioPositionsGroupProps {
  priceCurve: Array<Array<number | string>>;
  positions: Position[];
  summary?: PortfolioSummary;
  strategy: Strategy;
}

interface PositionRowProps {
  position: Position;
}

const PositionRow: FC<PositionRowProps> = ({ position }) => {
  const stockColors = useStockColors();
  const changeType = getChangeType(position.unrealized_pnl);

  return (
    <TableRow>
      <TableCell>
        <div className="flex items-center gap-2">
          <PngIcon
            src={getCoinCapIcon(position.symbol)}
            callback={ValueCellAgentPng}
          />
          <p className="font-medium text-gray-950 text-sm">{position.symbol}</p>
        </div>
      </TableCell>
      <TableCell>
        <Badge
          variant="outline"
          className={
            position.type === "LONG" ? "text-rose-600" : "text-emerald-600"
          }
        >
          {position.type}
        </Badge>
      </TableCell>
      <TableCell>
        <p className="font-medium text-gray-950 text-sm">
          {position.leverage}X
        </p>
      </TableCell>
      <TableCell>
        <p className="font-medium text-gray-950 text-sm">{position.quantity}</p>
      </TableCell>
      <TableCell>
        <p
          className="font-medium text-sm"
          style={{ color: stockColors[changeType] }}
        >
          {formatChange(position.unrealized_pnl, "", 2)} (
          {formatChange(position.unrealized_pnl_pct, "", 2)}%)
        </p>
      </TableCell>
    </TableRow>
  );
};

const PortfolioPositionsGroup: FC<PortfolioPositionsGroupProps> = ({
  summary,
  priceCurve,
  positions,
  strategy,
}) => {
  const { t } = useTranslation();
  const sharePortfolioModalRef = useRef<SharePortfolioCardRef>(null);

  const stockColors = useStockColors();
  const changeType = getChangeType(summary?.total_pnl);
  const { name, avatar } = useSystemInfo();
  const isLogin = useIsLoggedIn();
  const { isTauriApp } = useTauriInfo();

  const hasPositions = positions.length > 0;
  const hasPriceCurve = priceCurve.length > 0;

  const { mutate: publishStrategy, isPending: isPublishing } =
    usePublishStrategy();

  const { refetch: refetchPerformance } = useStrategyPerformance(
    strategy.strategy_id,
  );

  const handlePublishToRankBoard = async () => {
    const { data } = await refetchPerformance();
    if (!data) return;
    const { exchange_id, ...rest } = data;

    publishStrategy({
      ...rest,
      exchange_id: exchange_id || "virtual",
      name,
      avatar,
    });
  };

  const handleSharePortfolio = async () => {
    const { data } = await refetchPerformance();
    if (!data) return;

    sharePortfolioModalRef.current?.open({
      ...data,
      total_pnl: summary?.total_pnl ?? 0,
      created_at: strategy.created_at,
    });
  };

  return (
    <div className="scroll-container flex flex-1 flex-col gap-8 p-6">
      {/* Portfolio Value History Section */}
      <div className="flex flex-1 flex-col gap-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-base text-gray-950">
            {t("strategy.portfolio.title")}
          </h3>
          {isTauriApp &&
            (isLogin ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button>
                    <SvgIcon name={Send} className="size-5" /> {t("strategy.action.publish")}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleSharePortfolio}>
                    <SvgIcon name={Share} className="size-5" /> {t("strategy.action.shareToSocial")}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={handlePublishToRankBoard}
                    disabled={isPublishing}
                  >
                    {isPublishing ? (
                      <Spinner className="size-5" />
                    ) : (
                      <SvgIcon name={Send} className="size-5" />
                    )}{" "}
                    {t("strategy.action.shareToRanking")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <LoginModal>
                <Button>
                  <SvgIcon name={Send} className="size-5" /> {t("strategy.action.publish")}
                </Button>
              </LoginModal>
            ))}
        </div>

        <div className="grid grid-cols-3 gap-4 text-nowrap">
          <div className="rounded-lg bg-gray-50 p-4">
            <p className="text-gray-500 text-sm">{t("strategy.portfolio.totalEquity")}</p>
            <p className="mt-1 font-semibold text-gray-900 text-lg">
              {numberFixed(summary?.total_value, 4)}
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 p-4">
            <p className="text-gray-500 text-sm">{t("strategy.portfolio.availableBalance")}</p>
            <p className="mt-1 font-semibold text-gray-900 text-lg">
              {numberFixed(summary?.cash, 4)}
            </p>
          </div>
          <div className="rounded-lg bg-gray-50 p-4">
            <p className="text-gray-500 text-sm">{t("strategy.portfolio.totalPnl")}</p>
            <p
              className="mt-1 font-semibold text-gray-900 text-lg"
              style={{ color: stockColors[changeType] }}
            >
              {numberFixed(summary?.total_pnl, 4)}
            </p>
          </div>
        </div>

        <div className="min-h-[400px] flex-1">
          {hasPriceCurve ? (
            <MultiLineChart data={priceCurve} showLegend={false} />
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl bg-gray-50">
              <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
                <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
                  <LineChart className="size-7 text-gray-400" />
                </div>
                <div className="flex flex-col gap-2">
                  <p className="font-semibold text-base text-gray-700">
                    {t("strategy.portfolio.noData")}
                  </p>
                  <p className="max-w-xs text-gray-500 text-sm leading-relaxed">
                    {t("strategy.portfolio.noDataDesc")}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Positions Section */}
      <div className="flex flex-col gap-4">
        <h3 className="font-semibold text-base text-gray-950">{t("strategy.positions.title")}</h3>
        {hasPositions ? (
          <Table className="scroll-container max-h-[260px]">
            <TableHeader>
              <TableRow>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">{t("strategy.positions.symbol")}</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">{t("strategy.positions.type")}</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">{t("strategy.positions.leverage")}</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">{t("strategy.positions.quantity")}</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">{t("strategy.positions.pnl")}</p>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.map((position, index) => (
                <PositionRow
                  key={`${position.symbol}-${index}`}
                  position={position}
                />
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="flex min-h-[240px] items-center justify-center rounded-xl bg-gray-50">
            <div className="flex flex-col items-center gap-4 px-6 py-10 text-center">
              <div className="flex size-12 items-center justify-center rounded-full bg-gray-100">
                <Wallet className="size-6 text-gray-400" />
              </div>
              <div className="flex flex-col gap-1.5">
                <p className="font-semibold text-gray-700 text-sm">
                  {t("strategy.positions.noOpen")}
                </p>
                <p className="max-w-xs text-gray-500 text-xs leading-relaxed">
                  {t("strategy.positions.noOpenDesc")}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      <SharePortfolioModal ref={sharePortfolioModalRef} />
    </div>
  );
};

export default memo(PortfolioPositionsGroup);
