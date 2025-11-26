import { Plus } from "lucide-react";
import { type FC, useEffect, useState } from "react";
import {
  useDeleteStrategy,
  useGetStrategyDetails,
  useGetStrategyHoldings,
  useGetStrategyList,
  useGetStrategyPortfolioSummary,
  useGetStrategyPriceCurve,
  useStopStrategy,
} from "@/api/strategy";
import { Button } from "@/components/ui/button";
import type { AgentViewProps } from "@/types/agent";
import type { Strategy } from "@/types/strategy";
import {
  CreateStrategyModal,
  PortfolioPositionsGroup,
  StrategyComposeList,
  TradeStrategyGroup,
} from "../strategy-items";

const EmptyIllustration = () => (
  <svg
    viewBox="0 0 258 185"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="h-[185px] w-[258px]"
  >
    <rect x="40" y="30" width="178" height="125" rx="8" fill="#F3F4F6" />
    <rect x="60" y="60" width="138" height="8" rx="4" fill="#E5E7EB" />
    <rect x="60" y="80" width="100" height="8" rx="4" fill="#E5E7EB" />
    <rect x="60" y="100" width="120" height="8" rx="4" fill="#E5E7EB" />
  </svg>
);

const StrategyAgentArea: FC<AgentViewProps> = () => {
  const { data: strategies = [], isLoading: isLoadingStrategies } =
    useGetStrategyList();
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(
    null,
  );

  const { data: composes = [] } = useGetStrategyDetails(
    selectedStrategy?.strategy_id,
  );

  const { data: priceCurve = [] } = useGetStrategyPriceCurve(
    selectedStrategy?.strategy_id,
  );
  const { data: positions = [] } = useGetStrategyHoldings(
    selectedStrategy?.strategy_id,
  );
  const { data: summary } = useGetStrategyPortfolioSummary(
    selectedStrategy?.strategy_id,
  );

  const { mutateAsync: stopStrategy } = useStopStrategy();
  const { mutateAsync: deleteStrategy } = useDeleteStrategy();

  useEffect(() => {
    if (strategies.length === 0) {
      setSelectedStrategy(null);
      return;
    }

    const hasSelectedStrategy =
      selectedStrategy &&
      strategies.some(
        (strategy) => strategy.strategy_id === selectedStrategy.strategy_id,
      );

    if (!selectedStrategy || !hasSelectedStrategy) {
      setSelectedStrategy(strategies[0]);
    }
  }, [strategies, selectedStrategy]);

  if (isLoadingStrategies) return null;

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left section: Strategy list */}
      <div className="flex w-96 flex-col gap-4 border-r py-6 *:px-6">
        <p className="font-semibold text-base">Trading Strategies</p>

        {strategies && strategies.length > 0 ? (
          <TradeStrategyGroup
            strategies={strategies}
            selectedStrategy={selectedStrategy}
            onStrategySelect={setSelectedStrategy}
            onStrategyStop={async (strategyId) =>
              await stopStrategy(strategyId)
            }
            onStrategyDelete={async (strategyId) => {
              await deleteStrategy(strategyId);
            }}
          />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-4">
            <EmptyIllustration />

            <div className="flex flex-col gap-3 text-center text-base text-gray-400">
              <p>No trading strategies</p>
              <p>Create your first trading strategy</p>
            </div>

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
        )}
      </div>

      {/* Right section: Trade History and Portfolio/Positions */}
      <div className="flex flex-1">
        {selectedStrategy ? (
          <>
            <StrategyComposeList
              composes={composes}
              tradingMode={selectedStrategy.trading_mode}
            />
            <PortfolioPositionsGroup
              summary={summary}
              priceCurve={priceCurve}
              positions={positions}
            />
          </>
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-8">
            <EmptyIllustration />
            <p className="font-normal text-base text-gray-400">
              No running strategies
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategyAgentArea;
