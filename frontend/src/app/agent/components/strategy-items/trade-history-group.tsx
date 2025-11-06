import { type FC, memo } from "react";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import { formatChange, getChangeType } from "@/lib/utils";
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

  // Extract symbol name (e.g., "BTC" from "BTC-USDT")
  const symbolName = trade.symbol.split("-")[0];

  // Format holding time from milliseconds to "XH XM" format
  const formatHoldingTime = (ms: number) => {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}H ${minutes}M`;
  };

  // Format price range
  const priceRange = trade.exit_price
    ? `$${trade.entry_price.toFixed(4)} → $${trade.exit_price.toFixed(4)}`
    : `$${trade.entry_price.toFixed(4)}`;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-gray-100 bg-gray-50 p-4">
      {/* Header: Symbol, Side/Type badges, and PnL */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <p className="font-semibold text-base text-gray-950">{symbolName}</p>
          <div className="flex items-center gap-1">
            {/* Side Badge */}
            <div className="flex items-center justify-center rounded-full bg-gray-100 px-2.5 py-1">
              <p className="font-semibold text-gray-700 text-xs">
                {trade.side}
              </p>
            </div>
            {/* Type Badge */}
            <div
              className={`flex items-center justify-center rounded-full border px-2.5 py-1 ${
                trade.type === "LONG"
                  ? "border-secondary-600"
                  : "border-success-600"
              }`}
            >
              <p
                className={`font-semibold text-xs ${
                  trade.type === "LONG"
                    ? "text-secondary-600"
                    : "text-success-600"
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
          {formatChange(trade.unrealized_pnl, "$", 2)}
        </p>
      </div>

      {/* Details */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between text-gray-500 text-sm">
          <p>Time</p>
          <p>{TimeUtils.format(trade.time, TIME_FORMATS.DATETIME_SHORT)}</p>
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
      </div>
    </div>
  );
};

const TradeHistoryGroup: FC<TradeHistoryGroupProps> = ({
  trades,
  tradingMode = "live",
}) => {
  return (
    <div className="flex size-full flex-col gap-4 border-r bg-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="font-semibold text-base text-gray-950">Trade History</p>
        <div className="flex h-[27px] items-center justify-center rounded-lg bg-gray-100 px-2.5 py-1.5">
          <p className="font-medium text-gray-950 text-sm">
            {tradingMode === "live" ? "Live Trading" : "Virtual Trading"}
          </p>
        </div>
      </div>

      {/* Trade List */}
      <ScrollContainer className="flex-1">
        <div className="flex flex-col gap-2">
          {trades.map((trade) => (
            <TradeHistoryCard key={trade.trade_id} trade={trade} />
          ))}
        </div>
      </ScrollContainer>
    </div>
  );
};

export default memo(TradeHistoryGroup);
