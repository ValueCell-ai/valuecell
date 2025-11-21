import { ChevronDown, History } from "lucide-react";
import { type FC, memo, useMemo, useState } from "react";
import { ValueCellAgentPng } from "@/assets/png";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { PngIcon } from "@/components/valuecell/png-icon";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import {
  formatChange,
  getChangeType,
  getCoinCapIcon,
  isNullOrUndefined,
  numberFixed,
} from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type {
  Strategy,
  StrategyAction,
  StrategyCompose,
} from "@/types/strategy";

interface StrategyComposeItemProps {
  compose: StrategyCompose;
}

const StrategyComposeItem: FC<StrategyComposeItemProps> = ({ compose }) => {
  const [isReasoningOpen, setIsReasoningOpen] = useState(false);

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-gray-100 bg-gray-50 p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-base text-gray-900">
          {`Cycle #${compose.cycle_index}`}
        </h3>
        <span className="text-gray-400 text-xs">
          {TimeUtils.formatUTC(compose.created_at, TIME_FORMATS.DATETIME)}
        </span>
      </div>

      {/* AI Reasoning Logic */}
      <p className="text-gray-400 text-xs">AI reasoning logic</p>
      <Collapsible open={isReasoningOpen} onOpenChange={setIsReasoningOpen}>
        <CollapsibleTrigger
          data-active={isReasoningOpen}
          className="flex w-full cursor-pointer items-start justify-between rounded-md border-gradient bg-white px-3 py-2 text-left"
        >
          <span
            className={`text-gray-700 text-sm leading-relaxed ${
              isReasoningOpen ? "" : "line-clamp-1"
            }`}
          >
            {compose.rationale}
          </span>
          <ChevronDown
            className={`mt-1 ml-2 size-4 shrink-0 text-gray-400 transition-transform duration-200 ${
              isReasoningOpen ? "rotate-180" : ""
            }`}
          />
        </CollapsibleTrigger>
      </Collapsible>

      {/* Perform Operation */}
      {compose.actions.length > 0 && (
        <>
          <p className="text-gray-400 text-xs">Perform operation</p>
          {compose.actions.map((action) => (
            <ActionItem key={action.instruction_id} action={action} />
          ))}
        </>
      )}
    </div>
  );
};

const ActionItem: FC<{ action: StrategyAction }> = ({ action }) => {
  const stockColors = useStockColors();

  const formatHoldingTime = (ms?: number) => {
    if (isNullOrUndefined(ms)) return "-";
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}H ${minutes}M`;
  };

  const priceRange = action.exit_price
    ? `${numberFixed(action.entry_price, 4)} → ${numberFixed(action.exit_price, 4)}`
    : `${numberFixed(action.entry_price, 4)}`;

  const [pnl_value, changeType] = useMemo(() => {
    if (!action.action.includes("close"))
      return ["-", getChangeType(undefined)];

    const changeType = getChangeType(action.realized_pnl);
    const formatPnl = formatChange(action.realized_pnl, "", 4);
    return [formatPnl, changeType];
  }, [action.realized_pnl, action.action]);

  return (
    <HoverCard openDelay={300}>
      <HoverCardTrigger asChild>
        <Button className="flex items-center justify-between rounded-md border-gradient bg-white p-3">
          <div className="flex items-center gap-2">
            <PngIcon
              src={getCoinCapIcon(action.symbol)}
              className="size-5"
              callback={ValueCellAgentPng}
            />
            <span className="font-medium text-gray-950 text-sm">
              {action.symbol}
            </span>

            <Badge variant="outline">{action.action_display}</Badge>
            <Badge variant="outline">{action.leverage}X</Badge>
          </div>

          {action.realized_pnl !== 0 && (
            <span
              className="font-medium text-sm"
              style={{ color: stockColors[changeType] }}
            >
              {pnl_value}
            </span>
          )}
        </Button>
      </HoverCardTrigger>
      <HoverCardContent
        className="rounded-xl border border-gray-200 p-4 shadow-[0_-4px_100px_8px_rgba(17,17,17,0.08)]"
        side="right"
      >
        {/* HoverCard Header */}
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PngIcon
              src={getCoinCapIcon(action.symbol)}
              className="size-5"
              callback={ValueCellAgentPng}
            />
            <span className="font-bold text-base text-gray-900">
              {action.symbol}
            </span>
          </div>

          <span
            className="font-medium"
            style={{ color: stockColors[changeType] }}
          >
            {pnl_value}
          </span>
        </div>

        {/* Popover Tags */}
        <div className="mb-4 flex gap-2">
          <span className="rounded-md bg-gray-100 px-2 py-1 font-medium text-gray-900 text-xs">
            {action.action_display}
          </span>
          <span className="rounded-md bg-gray-100 px-2 py-1 font-medium text-gray-900 text-xs">
            {action.leverage}X
          </span>
        </div>

        {/* Data Grid */}
        <div className="mb-4 grid grid-cols-[auto_1fr] gap-y-1 text-nowrap text-gray-500 text-xs">
          <span>Time</span>
          <span className="text-right">
            {TimeUtils.formatUTC(
              action.exit_at ?? action.entry_at,
              TIME_FORMATS.DATETIME,
            )}
          </span>

          <span>Price</span>
          <span className="text-right">{priceRange}</span>

          <span>Quantity</span>
          <span className="text-right">{action.quantity}</span>

          <span>Holding time</span>
          <span className="text-right">
            {formatHoldingTime(action.holding_time_ms)}
          </span>

          <span>Trading Fee</span>
          <span className="text-right">{-numberFixed(action.fee_cost, 4)}</span>
        </div>

        {/* Reasoning Box */}
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="mb-1 font-medium text-gray-900 text-xs">Reasoning</p>
          <p className="text-gray-500 text-xs leading-relaxed">
            {action.rationale}
          </p>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
};

interface StrategyComposeListProps {
  composes: StrategyCompose[];
  tradingMode: Strategy["trading_mode"];
}

const StrategyComposeList: FC<StrategyComposeListProps> = ({
  composes,
  tradingMode,
}) => {
  return (
    <div className="flex w-[420px] flex-col overflow-hidden border-r bg-white">
      <div className="flex items-center justify-between px-6 py-4">
        <h3 className="font-semibold text-base text-gray-950">
          Trading History
        </h3>

        <p className="rounded-md bg-gray-100 px-2.5 py-1 font-medium text-gray-950 text-sm">
          {tradingMode === "live" ? "Live Trading" : "Virtual Trading"}
        </p>
      </div>

      <ScrollContainer className="flex-1 px-6">
        {composes.length > 0 ? (
          <div className="flex flex-col gap-4">
            {composes.map((compose) => (
              <StrategyComposeItem key={compose.compose_id} compose={compose} />
            ))}
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
              <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
                <History className="size-7 text-gray-400" />
              </div>
              <div className="flex flex-col gap-2">
                <p className="font-semibold text-base text-gray-700">
                  No trade history
                </p>
                <p className="max-w-[280px] text-gray-500 text-sm leading-relaxed">
                  Your completed trades will appear here
                </p>
              </div>
            </div>
          </div>
        )}
      </ScrollContainer>
    </div>
  );
};

export default memo(StrategyComposeList);
