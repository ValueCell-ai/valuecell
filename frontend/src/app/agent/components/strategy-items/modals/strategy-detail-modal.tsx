import {
  type FC,
  type RefObject,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { useStrategyPerformance } from "@/api/strategy";
import { ValueCellAgentPng } from "@/assets/png";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import CopyStrategyModal, {
  type CopyStrategyModelRef,
} from "@/components/valuecell/modal/copy-strategy-modal";
import { getChangeType, numberFixed } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import { useIsLoggedIn, useSystemInfo } from "@/store/system-store";
export interface StrategyDetailModalRef {
  open: (strategyId: number) => void;
}

interface StrategyDetailModalProps {
  ref?: RefObject<StrategyDetailModalRef | null>;
}

const StrategyDetailModal: FC<StrategyDetailModalProps> = ({ ref }) => {
  const stockColors = useStockColors();
  const [open, setOpen] = useState(false);
  const [strategyId, setStrategyId] = useState<number | null>(null);
  const copyStrategyModalRef = useRef<CopyStrategyModelRef>(null);
  const {
    data: strategyDetail,
    isLoading: isLoadingStrategyDetail,
    refetch: refetchStrategyDetail,
  } = useStrategyPerformance(strategyId);
  const { name, avatar } = useSystemInfo();
  const isLoggedin = useIsLoggedIn();

  useEffect(() => {
    if (strategyId) {
      refetchStrategyDetail();
    }
  }, [strategyId, refetchStrategyDetail]);

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
        <div className="scroll-container">
          {isLoadingStrategyDetail || !strategyDetail ? (
            <div className="py-8 text-center">Loading details...</div>
          ) : (
            <div className="grid gap-4 py-4">
              <div className="flex items-center gap-4">
                <Avatar className="size-16">
                  <AvatarImage
                    src={isLoggedin ? avatar : ValueCellAgentPng}
                    alt={name}
                  />
                  <AvatarFallback>{isLoggedin ? name[0] : "V"}</AvatarFallback>
                </Avatar>
                <h3 className="font-bold text-lg">
                  {isLoggedin ? name : "ValueCell"}
                </h3>
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
        </div>

        <DialogFooter className="mt-auto">
          <Button
            className="w-full"
            onClick={async () => {
              copyStrategyModalRef.current?.open({
                llm_model_config: {
                  provider: strategyDetail?.llm_provider || "",
                  model_id: strategyDetail?.llm_model_id || "",
                  api_key: "",
                },
                exchange_config: {
                  exchange_id: strategyDetail?.exchange_id || "",
                  trading_mode: strategyDetail?.trading_mode || "virtual",
                  api_key: "",
                  secret_key: "",
                  passphrase: "",
                  wallet_address: "",
                  private_key: "",
                },
                trading_config: {
                  strategy_name: "",
                  strategy_type:
                    strategyDetail?.strategy_type || "PromptBasedStrategy",
                  initial_capital: strategyDetail?.initial_capital || 0,
                  max_leverage: strategyDetail?.max_leverage || 0,
                  symbols: strategyDetail?.symbols || [],
                  decide_interval: strategyDetail?.decide_interval || 0,
                  prompt: strategyDetail?.prompt || "",
                  prompt_name: strategyDetail?.prompt_name || "",
                },
              });
            }}
          >
            Duplicate
          </Button>
        </DialogFooter>
      </DialogContent>

      <CopyStrategyModal ref={copyStrategyModalRef} />
    </Dialog>
  );
};

export default StrategyDetailModal;
