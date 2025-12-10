import { useStore } from "@tanstack/react-form";
import { AlertCircleIcon } from "lucide-react";
import type { FC, RefObject } from "react";
import { memo, useImperativeHandle, useState } from "react";
import { useGetModelProviderDetail } from "@/api/setting";
import {
  useCreateStrategy,
  useGetStrategyList,
  useGetStrategyPrompts,
} from "@/api/strategy";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import CloseButton from "@/components/valuecell/button/close-button";
import { AIModelForm } from "@/components/valuecell/form/ai-model-form";
import {
  EXCHANGE_OPTIONS,
  ExchangeForm,
} from "@/components/valuecell/form/exchange-form";
import { TradingStrategyForm } from "@/components/valuecell/form/trading-strategy-form";
import { StepIndicator } from "@/components/valuecell/step-indicator";
import { TRADING_SYMBOLS } from "@/constants/agent";
import {
  aiModelSchema,
  exchangeSchema,
  tradingStrategySchema,
} from "@/constants/schema";
import { useAppForm } from "@/hooks/use-form";
import { tracker } from "@/lib/tracker";
import type { CreateStrategy, Strategy } from "@/types/strategy";

export interface CreateStrategyModelRef {
  open: (data?: CreateStrategy) => void;
}
interface CreateStrategyModalProps {
  children?: React.ReactNode;
  ref?: RefObject<CreateStrategyModelRef | null>;
}

const STEPS = [
  { step: 1, title: "AI Models" },
  { step: 2, title: "Exchanges" },
  { step: 3, title: "Trading strategy" },
];

const CreateStrategyModal: FC<CreateStrategyModalProps> = ({
  ref,
  children,
}) => {
  const [open, setOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const { data: prompts = [] } = useGetStrategyPrompts();
  const { data: strategies = [] } = useGetStrategyList();
  const { mutateAsync: createStrategy, isPending: isCreatingStrategy } =
    useCreateStrategy();

  // Step 1 Form: AI Models
  const form1 = useAppForm({
    defaultValues: {
      provider: "",
      model_id: "",
      api_key: "",
    },
    validators: {
      onSubmit: aiModelSchema,
    },
    onSubmit: () => {
      setCurrentStep(2);
    },
  });

  const provider = useStore(form1.store, (state) => state.values.provider);
  const { data: modelProviderDetail } = useGetModelProviderDetail(provider);

  // Step 2 Form: Exchanges
  const form2 = useAppForm({
    defaultValues: {
      trading_mode: "live" as "live" | "virtual",
      exchange_id: "okx",
      api_key: "",
      secret_key: "",
      passphrase: "",
      wallet_address: "",
      private_key: "",
    },
    validators: {
      onSubmit: exchangeSchema,
    },
    onSubmit: () => {
      const modelId = form1.state.values.model_id;
      const modelName =
        modelProviderDetail?.models.find((m) => m.model_id === modelId)
          ?.model_name || modelId;

      const { trading_mode, exchange_id } = form2.state.values;
      const exchangeName =
        trading_mode === "virtual"
          ? "Virtual"
          : EXCHANGE_OPTIONS.find((ex) => ex.value === exchange_id)?.label ||
            exchange_id;

      const baseName = `${modelName}-${exchangeName}`;
      let newName = baseName;
      let counter = 1;

      while (strategies.some((s) => s.strategy_name === newName)) {
        newName = `${baseName}-${counter}`;
        counter++;
      }

      form3.setFieldValue("strategy_name", newName);
      setCurrentStep(3);
    },
  });

  // Step 3 Form: Trading Strategy
  const form3 = useAppForm({
    defaultValues: {
      strategy_type: "PromptBasedStrategy" as Strategy["strategy_type"],
      strategy_name: "",
      initial_capital: 1000,
      max_leverage: 2,
      decide_interval: 60,
      symbols: TRADING_SYMBOLS,
      template_id: prompts.length > 0 ? prompts[0].id : "",
    },
    validators: {
      onSubmit: tradingStrategySchema,
    },
    onSubmit: async ({ value }) => {
      const payload = {
        llm_model_config: form1.state.values,
        exchange_config: form2.state.values,
        trading_config: value,
      };

      const { code, msg } = await createStrategy(payload);
      if (code !== 0) {
        setError(msg);
        return;
      }

      tracker.send("use", { agent_name: "StrategyAgent" });
      resetAll();
    },
  });

  const resetAll = () => {
    setCurrentStep(1);
    form1.reset();
    form2.reset();
    form3.reset();
    setError(null);
    setOpen(false);
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  useImperativeHandle(ref, () => ({
    open: (data) => {
      if (data) {
        form1.reset(data.llm_model_config);
        form2.reset(data.exchange_config);
        form3.reset(data.trading_config);
      }
      setOpen(true);
    },
  }));

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>

      <DialogContent
        className="flex max-h-[90vh] min-h-96 flex-col"
        showCloseButton={false}
        aria-describedby={undefined}
      >
        <DialogTitle className="flex flex-col gap-4 px-1">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">Add trading strategy</h2>
            <CloseButton onClick={resetAll} />
          </div>

          <StepIndicator steps={STEPS} currentStep={currentStep} />
        </DialogTitle>

        {/* Form content with scroll */}
        <div className="scroll-container px-1 py-2">
          {/* Step 1: AI Models */}
          {currentStep === 1 && <AIModelForm form={form1} />}

          {/* Step 2: Exchanges */}
          {currentStep === 2 && <ExchangeForm form={form2} />}

          {/* Step 3: Trading Strategy */}
          {currentStep === 3 && (
            <TradingStrategyForm
              form={form3}
              prompts={prompts}
              tradingMode={form2.state.values.trading_mode}
            />
          )}
        </div>

        <DialogFooter className="mt-auto flex flex-col! gap-2">
          {error && (
            <Alert variant="destructive">
              <AlertCircleIcon />
              <AlertTitle>Error Creating Strategy</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="grid w-full grid-cols-2 gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={currentStep === 1 ? resetAll : handleBack}
              className="border-gray-100 py-4 font-semibold text-base"
            >
              {currentStep === 1 ? "Cancel" : "Back"}
            </Button>
            <Button
              type="button"
              disabled={isCreatingStrategy}
              onClick={async () => {
                switch (currentStep) {
                  case 1:
                    await form1.handleSubmit();
                    break;
                  case 2:
                    await form2.handleSubmit();
                    break;
                  case 3:
                    await form3.handleSubmit();
                }
              }}
              className="relative py-4 font-semibold text-base text-white hover:bg-gray-800"
            >
              {isCreatingStrategy && <Spinner className="absolute left-4" />}
              {currentStep === 3 ? "Confirm" : "Next"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default memo(CreateStrategyModal);
