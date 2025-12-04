import { type FC, type RefObject, useImperativeHandle, useState } from "react";
import { useGetStrategyDetail } from "@/api/system";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getChangeType, numberFixed } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import ScrollContainer from "../scroll/scroll-container";

export interface StrategyDetailModalRef {
  open: (strategyId: number) => void;
}

interface StrategyDetailModalProps {
  ref: RefObject<StrategyDetailModalRef | null>;
}

const StrategyDetailModal: FC<StrategyDetailModalProps> = ({ ref }) => {
  const stockColors = useStockColors();
  const [open, setOpen] = useState(false);
  const [strategyId, setStrategyId] = useState<number | null>(null);

  const { data: strategyDetail, isLoading: isLoadingStrategyDetail } =
    useGetStrategyDetail(strategyId);

  useImperativeHandle(ref, () => ({
    open: (strategyId: number) => {
      setStrategyId(strategyId);
      setOpen(true);
    },
  }));

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent
        className="flex max-h-[90vh] min-h-96 flex-col"
        aria-describedby={undefined}
      >
        <DialogHeader>
          <DialogTitle>Strategy Details</DialogTitle>
        </DialogHeader>
        <ScrollContainer>
          {isLoadingStrategyDetail || !strategyDetail ? (
            <div className="py-8 text-center">Loading details...</div>
          ) : (
            <div className="grid gap-4 py-4">
              <div className="flex items-center gap-4">
                <Avatar className="size-16">
                  <AvatarImage
                    src={strategyDetail.avatar}
                    alt={strategyDetail.name}
                  />
                  <AvatarFallback>{strategyDetail.name[0]}</AvatarFallback>
                </Avatar>
                <h3 className="font-bold text-lg">{strategyDetail.name}</h3>
                <div className="ml-auto text-right">
                  <div
                    className="font-bold text-2xl"
                    style={{
                      color:
                        stockColors[
                          getChangeType(strategyDetail.return_rate_pct)
                        ],
                    }}
                  >
                    {numberFixed(strategyDetail.return_rate_pct, 2)}%
                  </div>
                  <div className="text-gray-500 text-sm">Return Rate</div>
                </div>
              </div>

              <div className="grid grid-cols-[auto_1fr] gap-y-2 text-nowrap text-sm [&>p]:text-gray-500 [&>span]:text-right">
                <p>Strategy Type</p>
                <span>{strategyDetail.strategy_type}</span>

                <p>Model Provider</p>
                <span>{strategyDetail.llm_provider}</span>

                <p>Model ID</p>
                <span>{strategyDetail.llm_model_id}</span>

                <p>Initial Capital</p>
                <span>{strategyDetail.initial_capital}</span>

                <p>Max Leverage</p>
                <span>{strategyDetail.max_leverage}x</span>

                <p>Trading Symbols</p>
                <span className="whitespace-normal">
                  {strategyDetail.symbols.join(", ")}
                </span>
              </div>

              <div className="gap-2">
                <span className="text-gray-500 text-sm">Prompt</span>
                <p className="rounded-md bg-gray-50 p-3 text-gray-700 text-sm">
                  {strategyDetail.prompt}
                </p>
              </div>
            </div>
          )}
        </ScrollContainer>

        <DialogFooter>
          <Button className="w-full">Copy and create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default StrategyDetailModal;
