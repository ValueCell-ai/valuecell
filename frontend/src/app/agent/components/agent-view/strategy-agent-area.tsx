import { Plus } from "lucide-react";
import type { FC } from "react";
import { useState } from "react";
import { useGetStrategyList } from "@/api/strategy";
import { Button } from "@/components/ui/button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import type { AgentViewProps } from "@/types/agent";
import { CreateStrategyModal } from "../strategy-items/create-strategy-modal";
import { TradeStrategyCard } from "../strategy-items/trade-strategy-card";

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
  const { data: strategies, isLoading } = useGetStrategyList();
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(
    null,
  );

  if (isLoading) return null;

  // Show empty state when there are no strategies
  return (
    <div className="flex flex-1">
      {/* Left section: Strategy list empty state */}
      <div className="flex w-96 flex-col gap-4 border-r p-6">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-base">Trading Strategies</p>
          {strategies && strategies.length > 0 && (
            <CreateStrategyModal
              trigger={
                <Button variant="ghost" size="icon" className="size-8">
                  <Plus className="size-5" />
                </Button>
              }
            />
          )}
        </div>

        <div className="flex flex-1 flex-col gap-4">
          {strategies && strategies.length > 0 ? (
            <ScrollContainer className="flex-1">
              <div className="flex flex-col gap-3 pr-2">
                {strategies.map((strategy) => (
                  <TradeStrategyCard
                    key={strategy.strategy_id}
                    strategy={strategy}
                    isSelected={selectedStrategyId === strategy.strategy_id}
                    onClick={() => setSelectedStrategyId(strategy.strategy_id)}
                  />
                ))}
              </div>
            </ScrollContainer>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center gap-4">
              <EmptyIllustration />

              <div className="flex flex-col gap-3 text-center text-base text-gray-400">
                <p>No trading strategies</p>
                <p>Create your first trading strategy</p>
              </div>

              <CreateStrategyModal
                trigger={
                  <Button
                    variant="outline"
                    className="w-full gap-3 rounded-lg py-4 text-base"
                  >
                    <Plus className="size-6" />
                    Add trading strategy
                  </Button>
                }
              />
            </div>
          )}
        </div>
      </div>
      {/* Right section: Strategy details empty state */}
      <div className="flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center gap-[31px]">
          <EmptyIllustration />
          <p className="text-[#9CA3AF] text-base leading-[22px]">
            No running strategies
          </p>
        </div>
      </div>
    </div>
  );
};

export default StrategyAgentArea;
