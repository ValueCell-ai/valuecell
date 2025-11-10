import { History } from "lucide-react";
import { type FC, memo } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import {
  formatChange,
  getChangeType,
  isNullOrUndefined,
  numberFixed,
} from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type { Trade } from "@/types/strategy";

interface TradeHistoryCardProps {
  trade: Trade;
}

interface TradeHistoryGroupProps {
  trades: Trade[];
  tradingMode?: "live" | "virtual";
}

const TradeHistoryCard: FC<TradeHistoryCardProps> = ({ trade }) => {
  const stockColors = useStockColors();
  const changeType = getChangeType(trade.unrealized_pnl);

  // Format holding time from milliseconds to "XH XM" format.
  const formatHoldingTime = (ms?: number) => {
    if (isNullOrUndefined(ms)) return "-";
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}H ${minutes}M`;
  };

  // Format price range
  const priceRange = trade.exit_price
    ? `$${numberFixed(trade.entry_price, 4)} → $${numberFixed(trade.exit_price, 4)}`
    : `$${numberFixed(trade.entry_price, 4)}`;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-gray-100 bg-gray-50 p-4">
      {/* Header: Symbol, Side/Type badges, and PnL */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <p className="font-semibold text-base text-gray-950">
            {trade.symbol}
          </p>
          <div className="flex items-center gap-1">
            {/* Side Badge */}
            <div className="flex items-center justify-center rounded-full bg-gray-100 px-2.5 py-1">
              <p className="font-semibold text-gray-700 text-xs">
                {trade.side}
              </p>
            </div>
            {/* Type Badge */}
            <div className="flex items-center justify-center rounded-full border border-gray-200 px-2.5 py-1">
              <p
                className={`font-semibold text-xs ${
                  trade.type === "LONG" ? "text-rose-600" : "text-emerald-600"
                }`}
              >
                {trade.type}
              </p>
            </div>
          </div>
        </div>
        {/* PnL */}
        <p
          className="font-semibold text-base"
          style={{ color: stockColors[changeType] }}
        >
          {formatChange(trade.unrealized_pnl, "", 4)}
        </p>
      </div>

      {/* Details */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between text-gray-500 text-sm">
          <p>Time</p>
          <p>{TimeUtils.formatUTC(trade.time, TIME_FORMATS.DATETIME_SHORT)}</p>
        </div>
        <div className="flex items-center justify-between text-gray-500 text-sm">
          <p>Price</p>
          <p>{priceRange}</p>
        </div>
        <div className="flex items-center justify-between text-gray-500 text-sm">
          <p>Quantity</p>
          <p>{trade.quantity}</p>
        </div>
        <div className="flex items-center justify-between text-gray-500 text-sm">
          <p>Holding time</p>
          <p>{formatHoldingTime(trade.holding_ms)}</p>
        </div>
        <div className="flex items-center justify-between text-gray-500 text-sm">
          <p>Reasoning</p>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="cursor-pointer hover:text-gray-700">
                View Detail
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">{trade.note}</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </div>
  );
};

const TradeHistoryGroup: FC<TradeHistoryGroupProps> = ({
  trades,
  tradingMode = "live",
}) => {
  const hasTrades = trades.length > 0;

  return (
    <div className="flex w-[360px] flex-col gap-4 border-r bg-white py-6 *:px-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="font-semibold text-base text-gray-950">Trade History</p>
        <p className="rounded-lg bg-gray-100 px-2.5 py-1 font-medium text-gray-950 text-sm">
          {tradingMode === "live" ? "Live Trading" : "Virtual Trading"}
        </p>
      </div>

      {/* Trade List */}
      {hasTrades ? (
        <ScrollContainer className="flex-1">
          <div className="flex flex-col gap-2">
            {trades.map((trade) => (
              <TradeHistoryCard key={trade.trade_id} trade={trade} />
            ))}
          </div>
        </ScrollContainer>
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
    </div>
  );
};

export default memo(TradeHistoryGroup);
