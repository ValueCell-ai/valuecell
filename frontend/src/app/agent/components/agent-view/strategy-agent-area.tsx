import { Plus } from "lucide-react";
import { type FC, useEffect } from "react";
import { useNavigate, useParams } from "react-router";
import {
  useDeleteStrategy,
  useGetStrategyDetails,
  useGetStrategyHoldings,
  useGetStrategyList,
  useGetStrategyPortfolioSummary,
  useGetStrategyPriceCurve,
  useStopStrategy,
} from "@/api/strategy";
import CreateStrategyModal from "@/app/agent/components/strategy-items/modals/create-strategy-modal";
import { Button } from "@/components/ui/button";
import type { AgentViewProps } from "@/types/agent";
import type { Strategy } from "@/types/strategy";
import {
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
  const { data: strategies = [], isLoading: isLoadingStrategies } = useGetStrategyList();
  
  const navigate = useNavigate();
  const { strategyId } = useParams();

  useEffect(() => {
    if (strategies.length > 0 && !strategyId) {
      navigate(`/agent/StrategyAgent/Strategies/${strategies[0].strategy_id}`);
    }
  }, [strategies, strategyId, navigate]);

  const selectedStrategy = strategyId ? 
    strategies.find(s => s.strategy_id.toString() === strategyId) || null : null;

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
            onStrategyStop={async (strategyId) =>
              await stopStrategy(strategyId)
            }
            onStrategyDelete={async (strategyId) => {
              await deleteStrategy(strategyId);
              if (selectedStrategy?.strategy_id === strategyId) {
                navigate('/agent/StrategyAgent/Strategies');
              }
            }}
            onStrategyCreated={(strategyId) => {
              navigate(`/agent/StrategyAgent/Strategies/${strategyId}`);
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
              strategy={selectedStrategy}
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
