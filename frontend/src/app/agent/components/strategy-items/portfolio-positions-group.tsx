import { LineChart, Wallet } from "lucide-react";
import { type FC, memo } from "react";
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
import { useStockColors } from "@/store/settings-store";
import type { Position } from "@/types/strategy";

interface PortfolioPositionsGroupProps {
  priceCurve: Array<Array<number | string>>;
  positions: Position[];
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
          {formatChange(position.unrealized_pnl_pct, "", 2)}%)
        </p>
      </TableCell>
    </TableRow>
  );
};

const PortfolioPositionsGroup: FC<PortfolioPositionsGroupProps> = ({
  priceCurve,
  positions,
}) => {
  const hasPositions = positions.length > 0;
  const hasPriceCurve = priceCurve.length > 0;

  return (
    <div className="flex flex-1 flex-col gap-8 overflow-y-scroll p-6">
      {/* Portfolio Value History Section */}
      <div className="flex flex-1 flex-col gap-6">
        <h3 className="font-semibold text-base text-gray-950">
          Portfolio Value History
        </h3>
        <div className="min-h-[400px] flex-1">
          {hasPriceCurve ? (
            <MultiLineChart data={priceCurve} showLegend={false} />
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border-2 border-gray-200 bg-gray-50/50">
              <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
                <div className="flex size-14 items-center justify-center rounded-full bg-gray-100">
                  <LineChart className="size-7 text-gray-400" />
                </div>
                <div className="flex flex-col gap-2">
                  <p className="font-semibold text-base text-gray-700">
                    No portfolio value data
                  </p>
                  <p className="max-w-xs text-gray-500 text-sm leading-relaxed">
                    Portfolio value chart will appear once trading begins
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Positions Section */}
      <div className="flex flex-col gap-4">
        <h3 className="font-semibold text-base text-gray-950">Positions</h3>
        {hasPositions ? (
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
                    <p className="font-normal text-gray-400 text-sm">
                      Leverage
                    </p>
                  </TableHead>
                  <TableHead>
                    <p className="font-normal text-gray-400 text-sm">
                      Quantity
                    </p>
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
        ) : (
          <div className="flex min-h-[240px] items-center justify-center rounded-xl border-2 border-gray-200 bg-gray-50/50">
            <div className="flex flex-col items-center gap-4 px-6 py-10 text-center">
              <div className="flex size-12 items-center justify-center rounded-full bg-gray-100">
                <Wallet className="size-6 text-gray-400" />
              </div>
              <div className="flex flex-col gap-1.5">
                <p className="font-semibold text-gray-700 text-sm">
                  No open positions
                </p>
                <p className="max-w-xs text-gray-500 text-xs leading-relaxed">
                  Positions will appear here when trades are opened
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(PortfolioPositionsGroup);
