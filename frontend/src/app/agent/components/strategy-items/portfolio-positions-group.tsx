import { type FC, memo } from "react";
import {
  useGetStrategyHoldings,
  useGetStrategyPriceCurve,
} from "@/api/strategy";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import MultiLineChart from "@/components/valuecell/charts/model-multi-line";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { formatChange, getChangeType } from "@/lib/utils";
import {
  MOCK_PORTFOLIO_PRICE_CURVE,
  MOCK_POSITIONS,
} from "@/mock/strategy-data";
import { useStockColors } from "@/store/settings-store";
import type { Position } from "@/types/strategy";

interface PortfolioPositionsGroupProps {
  strategyId?: string;
}

interface PositionRowProps {
  position: Position;
}

const PositionRow: FC<PositionRowProps> = ({ position }) => {
  const stockColors = useStockColors();
  const changeType = getChangeType(position.unrealized_pnl);

  // Extract symbol name (e.g., "BTC" from "BTC-USDT")
  const symbolName = position.symbol.split("-")[0];

  return (
    <TableRow>
      <TableCell>
        <p className="font-medium text-gray-950 text-sm">{symbolName}</p>
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
          {formatChange(position.unrealized_pnl_pct, "", 1)}%)
        </p>
      </TableCell>
    </TableRow>
  );
};

const PortfolioPositionsGroup: FC<PortfolioPositionsGroupProps> = ({
  strategyId,
}) => {
  const {
    data: priceCurve = MOCK_PORTFOLIO_PRICE_CURVE[strategyId ?? ""] || {
      data: [],
      create_time: "",
    },
  } = useGetStrategyPriceCurve(strategyId);

  const { data: positions = MOCK_POSITIONS[strategyId ?? ""] || [] } =
    useGetStrategyHoldings(strategyId);

  return (
    <div className="flex size-full flex-col gap-8 overflow-hidden p-6">
      {/* Portfolio Value History Section */}
      <div className="flex flex-1 flex-col gap-6">
        <h3 className="font-semibold text-base text-gray-950">
          Portfolio Value History
        </h3>
        <div className="min-h-[400px] flex-1">
          {priceCurve.data.length > 0 && (
            <MultiLineChart data={priceCurve.data} showLegend={false} />
          )}
        </div>
      </div>

      {/* Positions Section */}
      <div className="flex flex-col gap-4">
        <h3 className="font-semibold text-base text-gray-950">Positions</h3>
        <ScrollContainer className="max-h-[260px]">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">Symbol</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">Type</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">Leverage</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">Quantity</p>
                </TableHead>
                <TableHead>
                  <p className="font-normal text-gray-400 text-sm">P&L</p>
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
        </ScrollContainer>
      </div>
    </div>
  );
};

export default memo(PortfolioPositionsGroup);
