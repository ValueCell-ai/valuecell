import { Plus } from "lucide-react";
import { type FC, memo } from "react";
import { StrategyStatus } from "@/assets/svg";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import SvgIcon from "@/components/valuecell/svg-icon";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { formatChange, getChangeType } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type { Strategy } from "@/types/strategy";
import CreateStrategyModal from "./create-strategy-modal";

interface TradeStrategyCardProps {
  strategy: Strategy;
  isSelected?: boolean;
  onClick?: () => void;
  onStop?: () => void;
}

interface TradeStrategyGroupProps {
  strategies: Strategy[];
  selectedStrategy?: Strategy | null;
  onStrategySelect?: (strategy: Strategy) => void;
  onStrategyStop?: (strategyId: string) => void;
}

const TradeStrategyCard: FC<TradeStrategyCardProps> = ({
  strategy,
  isSelected = false,
  onClick,
  onStop,
}) => {
  const stockColors = useStockColors();
  const changeType = getChangeType(strategy.unrealized_pnl_pct);
  return (
    <div
      onClick={onClick}
      data-active={isSelected}
      className="flex cursor-pointer flex-col gap-3 rounded-lg border border-gradient border-solid px-3 py-4"
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

      {/* Model and Exchange Info */}
      <div className="flex items-center gap-2 font-medium text-gray-400 text-sm">
        <p>{strategy.model_id}</p>
        <p>{strategy.exchange_id}</p>
      </div>

      {/* PnL, Trading Mode, and Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <p
            className="font-medium text-sm"
            style={{ color: stockColors[changeType] }}
          >
            {formatChange(strategy.unrealized_pnl, "", 2)} (
            {formatChange(strategy.unrealized_pnl_pct, "%", 1)})
          </p>

          {/* Trading Mode Badge */}
          <div className="rounded px-0 py-0.5">
            <p className="font-normal text-gray-700 text-xs">
              {strategy.trading_mode === "live" ? "Live" : "Virtual"}
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <Button
          variant="ghost"
          disabled={strategy.status === "stopped"}
          size={"sm"}
          onClick={onStop}
          className="flex items-center gap-2.5 rounded-md px-2.5 py-1"
        >
          {strategy.status === "running" && (
            <SvgIcon name={StrategyStatus} className="size-4" />
          )}
          <p className="font-medium text-gray-700 text-sm">
            {strategy.status === "running" ? "Running" : "Stopped"}
          </p>
        </Button>
      </div>
    </div>
  );
};

const TradeStrategyGroup: FC<TradeStrategyGroupProps> = ({
  strategies,
  selectedStrategy,
  onStrategySelect,
  onStrategyStop,
}) => {
  return (
    <>
      <ScrollContainer className="min-w-80 flex-1">
        <div className="flex flex-col gap-3">
          {strategies.map((strategy) => (
            <TradeStrategyCard
              key={strategy.strategy_id}
              strategy={strategy}
              isSelected={
                selectedStrategy?.strategy_id === strategy.strategy_id
              }
              onClick={() => onStrategySelect?.(strategy)}
              onStop={() => onStrategyStop?.(strategy.strategy_id)}
            />
          ))}
        </div>
      </ScrollContainer>
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
