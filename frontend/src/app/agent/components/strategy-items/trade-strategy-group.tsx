import { Copy, Eye, MoreVertical, Plus, TrendingUp } from "lucide-react";
import { type FC, memo, useRef, useState } from "react";
import { useStrategyPerformance } from "@/api/strategy";
import { DeleteStrategy, StrategyStatus } from "@/assets/svg";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import SvgIcon from "@/components/valuecell/icon/svg-icon";
import CopyStrategyModal, {
  type CopyStrategyModelRef,
} from "@/components/valuecell/modal/copy-strategy-modal";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { formatChange, getChangeType } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type { Strategy } from "@/types/strategy";
import CreateStrategyModal from "./modals/create-strategy-modal";
import StrategyDetailModal, {
  type StrategyDetailModalRef,
} from "./modals/strategy-detail-modal";

interface TradeStrategyCardProps {
  strategy: Strategy;
  isSelected?: boolean;
  onClick?: () => void;
  onStop?: () => void;
  onDelete?: () => void;
}

interface TradeStrategyGroupProps {
  strategies: Strategy[];
  selectedStrategy?: Strategy | null;
  onStrategySelect?: (strategy: Strategy) => void;
  onStrategyStop?: (strategyId: number) => void;
  onStrategyDelete?: (strategyId: number) => void;
}

const TradeStrategyCard: FC<TradeStrategyCardProps> = ({
  strategy,
  isSelected = false,
  onClick,
  onStop,
  onDelete,
}) => {
  const stockColors = useStockColors();
  const changeType = getChangeType(strategy.total_pnl_pct);

  const [isDeleting, setIsDeleting] = useState(false);
  const strategyDetailModalRef = useRef<StrategyDetailModalRef>(null);
  const copyStrategyModalRef = useRef<CopyStrategyModelRef>(null);

  const { refetch: refetchStrategyPerformance } = useStrategyPerformance(
    strategy.strategy_id,
  );

  return (
    <div
      onClick={onClick}
      data-active={isSelected}
      className="flex cursor-pointer flex-col gap-2 rounded-lg border border-gradient border-solid px-3 py-4"
    >
      {/* Header: Name and Time */}
      <div className="flex items-center justify-between">
        <p className="font-medium text-base text-gray-950 leading-[22px]">
          {strategy.strategy_name}
        </p>
        <p className="font-normal text-gray-400 text-xs">
          {TimeUtils.formatUTC(
            strategy.created_at,
            TIME_FORMATS.DATETIME_SHORT,
          )}
        </p>
      </div>

      <div className="flex items-center gap-2">
        {strategy.strategy_type && (
          <p className="rounded-sm bg-gray-100 px-2 py-1 text-gray-700 text-xs">
            {strategy.strategy_type}
          </p>
        )}
        <p className="rounded-sm bg-gray-100 px-2 py-1 text-gray-700 text-xs">
          {strategy.trading_mode === "live" ? "Live" : "Virtual"}
        </p>
      </div>

      {/* Model and Exchange Info */}
      <div className="flex items-center gap-2 font-medium text-gray-400 text-sm">
        <p>{strategy.model_id}</p>
        <p>{strategy.exchange_id}</p>
      </div>

      {/* PnL, Trading Mode, and Status */}
      <div className="flex items-center justify-between">
        <p
          className="font-medium text-sm"
          style={{ color: stockColors[changeType] }}
        >
          {formatChange(strategy.total_pnl, "", 2)} (
          {formatChange(strategy.total_pnl_pct, "%", 2)})
        </p>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          {strategy.status === "stopped" && strategy.stop_reason ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <p className="font-medium text-gray-400 text-sm">Stopped</p>
              </TooltipTrigger>
              <TooltipContent side="top" className="wrap-break-word max-w-xs">
                {strategy.stop_reason}
              </TooltipContent>
            </Tooltip>
          ) : (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  disabled={strategy.status === "stopped"}
                  size="sm"
                  className="flex items-center gap-2.5 rounded-md px-2.5 py-1"
                >
                  {strategy.status === "running" && (
                    <SvgIcon name={StrategyStatus} className="size-4" />
                  )}
                  <p className="font-medium text-gray-700 text-sm">
                    {strategy.status === "running" ? "Running" : "Stopped"}
                  </p>
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Stop Trading Strategy?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Stopping the strategy "{strategy.strategy_name}" will stop
                    it immediately and trigger a forced liquidation. Do you want
                    to proceed?
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={onStop}>
                    Confirm Stop
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem
                onClick={() =>
                  strategyDetailModalRef.current?.open(strategy.strategy_id)
                }
              >
                <Eye className="ml-1 size-5" />
                Details
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={async () => {
                  const { data: strategyDetail } =
                    await refetchStrategyPerformance();

                  copyStrategyModalRef.current?.open({
                    llm_model_config: {
                      provider: strategyDetail?.llm_provider || "",
                      model_id: strategyDetail?.llm_model_id || "",
                      api_key: "",
                    },
                    exchange_config: {
                      exchange_id: strategyDetail?.exchange_id || "",
                      trading_mode: strategyDetail?.trading_mode || "virtual",
                      api_key: "",
                      secret_key: "",
                      passphrase: "",
                      wallet_address: "",
                      private_key: "",
                    },
                    trading_config: {
                      strategy_name: "",
                      strategy_type:
                        strategyDetail?.strategy_type || "PromptBasedStrategy",
                      initial_capital: strategyDetail?.initial_capital || 1000,
                      max_leverage: strategyDetail?.max_leverage || 2,
                      symbols: strategyDetail?.symbols || [],
                      decide_interval: strategyDetail?.decide_interval || 60,
                      prompt: strategyDetail?.prompt || "",
                      prompt_name: strategyDetail?.prompt_name || "",
                    },
                  });
                }}
              >
                <Copy className="ml-1 size-5" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setIsDeleting(true)}>
                <SvgIcon
                  name={DeleteStrategy}
                  className="size-6 text-red-500"
                />{" "}
                <span className="text-red-500">Delete</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <AlertDialog open={isDeleting} onOpenChange={setIsDeleting}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Strategy?</AlertDialogTitle>
            <AlertDialogDescription>
              Deleting the strategy "{strategy.strategy_name}" will stop it
              immediately and trigger a forced liquidation. Do you want to
              proceed?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>
              Confirm Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <StrategyDetailModal ref={strategyDetailModalRef} />
      <CopyStrategyModal ref={copyStrategyModalRef} />
    </div>
  );
};

const TradeStrategyGroup: FC<TradeStrategyGroupProps> = ({
  strategies,
  selectedStrategy,
  onStrategySelect,
  onStrategyStop,
  onStrategyDelete,
}) => {
  const hasStrategies = strategies.length > 0;

  return (
    <>
      {hasStrategies ? (
        <div className="scroll-container flex flex-1 flex-col gap-3">
          {strategies.map((strategy) => (
            <TradeStrategyCard
              key={strategy.strategy_id}
              strategy={strategy}
              isSelected={
                selectedStrategy?.strategy_id === strategy.strategy_id
              }
              onClick={() => onStrategySelect?.(strategy)}
              onStop={() => onStrategyStop?.(strategy.strategy_id)}
              onDelete={() => onStrategyDelete?.(strategy.strategy_id)}
            />
          ))}
        </div>
      ) : (
        <div className="flex w-80 items-center justify-center rounded-xl border-2 border-gray-200 border-dashed bg-gray-50/50">
          <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
              <TrendingUp className="size-7 text-gray-400" />
            </div>
            <div className="flex flex-col gap-2">
              <p className="font-semibold text-base text-gray-700">
                No trading strategies
              </p>
              <p className="max-w-xs text-gray-500 text-sm leading-relaxed">
                Create your first strategy to start trading
              </p>
            </div>
          </div>
        </div>
      )}

      <div>
        <CreateStrategyModal>
          <Button
            variant="outline"
            className="w-full gap-3 rounded-lg py-4 text-base"
          >
            <Plus className="size-6" />
            Add trading strategy
          </Button>
        </CreateStrategyModal>
      </div>
    </>
  );
};

export default memo(TradeStrategyGroup);
