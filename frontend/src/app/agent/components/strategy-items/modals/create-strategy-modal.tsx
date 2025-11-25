import { Check } from "lucide-react";
import type { FC } from "react";
import { memo, useState } from "react";
import { z } from "zod";
import { useCreateStrategy, useGetStrategyPrompts } from "@/api/strategy";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import CloseButton from "@/components/valuecell/button/close-button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { TRADING_SYMBOLS } from "@/constants/agent";
import { useAppForm } from "@/hooks/use-form";
import type { Strategy } from "@/types/strategy";
import { AIModelForm } from "../forms/ai-model-form";
import { ExchangeForm } from "../forms/exchange-form";
import { TradingStrategyForm } from "../forms/trading-strategy-form";

interface CreateStrategyModalProps {
  children?: React.ReactNode;
}

type StepNumber = 1 | 2 | 3;

// Step 1 Schema: AI Models
const step1Schema = z.object({
  provider: z.string().min(1, "Model platform is required"),
  model_id: z.string().min(1, "Model selection is required"),
  api_key: z.string().min(1, "API key is required"),
});

// Step 2 Schema: Exchanges (conditional validation with superRefine)
// Base schema with all fields optional (empty strings allowed)
const baseStep2Fields = {
  exchange_id: z.string(),
  api_key: z.string(),
  secret_key: z.string(),
  passphrase: z.string(),
  wallet_address: z.string(),
  private_key: z.string(),
};

const step2Schema = z.union([
  // Virtual Trading
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("virtual"),
  }),

  // Live Trading - Hyperliquid
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("live"),
    exchange_id: z.literal("hyperliquid"),
    wallet_address: z
      .string()
      .min(1, "Wallet Address is required for Hyperliquid"),
    private_key: z.string().min(1, "Private Key is required for Hyperliquid"),
  }),

  // Live Trading - OKX & Coinbase (Require Passphrase)
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("live"),
    exchange_id: z.enum(["okx", "coinbaseexchange"]),
    api_key: z.string().min(1, "API key is required"),
    secret_key: z.string().min(1, "Secret key is required"),
    passphrase: z.string().min(1, "Passphrase is required"),
  }),

  // Live Trading - Standard Exchanges
  z.object({
    ...baseStep2Fields,
    trading_mode: z.literal("live"),
    exchange_id: z.enum(["binance", "blockchaincom", "gate", "mexc"]),
    api_key: z.string().min(1, "API key is required"),
    secret_key: z.string().min(1, "Secret key is required"),
  }),
]);

// Step 3 Schema: Trading Strategy
const step3Schema = z.object({
  strategy_type: z.enum(["PromptBasedStrategy", "GridStrategy"]),
  strategy_name: z.string().min(1, "Strategy name is required"),
  initial_capital: z.number().min(1, "Initial capital must be at least 1"),
  max_leverage: z
    .number()
    .min(1, "Leverage must be at least 1")
    .max(5, "Leverage must be at most 5"),
  symbols: z.array(z.string()).min(1, "At least one symbol is required"),
  template_id: z.string().min(1, "Template selection is required"),
});

const STEPS = [
  { number: 1 as const, title: "AI Models" },
  { number: 2 as const, title: "Exchanges" },
  { number: 3 as const, title: "Trading strategy" },
];

const StepIndicator: FC<{ currentStep: StepNumber }> = ({ currentStep }) => {
  const getStepState = (stepNumber: StepNumber) => ({
    isCompleted: stepNumber < currentStep,
    isCurrent: stepNumber === currentStep,
    isActive: stepNumber <= currentStep,
    isLast: stepNumber === STEPS.length,
  });

  const renderStepNumber = (
    step: StepNumber,
    isCurrent: boolean,
    isCompleted: boolean,
  ) => {
    if (isCompleted) {
      return (
        <div className="flex size-6 items-center justify-center rounded-full bg-gray-950">
          <Check className="size-3 text-white" />
        </div>
      );
    }

    return (
      <div className="relative flex size-6 items-center justify-center">
        <div
          className={`absolute inset-0 rounded-full border-2 ${
            isCurrent ? "border-gray-950 bg-gray-950" : "border-black/40"
          }`}
        />
        <span
          className={`relative font-semibold text-base ${
            isCurrent ? "text-white" : "text-black/40"
          }`}
        >
          {step}
        </span>
      </div>
    );
  };

  return (
    <div className="flex items-start">
      {STEPS.map((step) => {
        const { isCompleted, isCurrent, isActive, isLast } = getStepState(
          step.number,
        );

        return (
          <div key={step.number} className="flex min-w-0 flex-1 items-start">
            <div className="flex w-full items-start gap-2">
              {/* Step number/icon */}
              <div className="shrink-0">
                {renderStepNumber(step.number, isCurrent, isCompleted)}
              </div>

              {/* Step title and connector line */}
              <div className="flex min-w-0 flex-1 items-center gap-3 pr-3">
                <span
                  className={`shrink-0 whitespace-nowrap text-base ${
                    isActive ? "text-black/90" : "text-black/40"
                  }`}
                >
                  {step.title}
                </span>

                {!isLast && (
                  <div
                    className={`h-0.5 min-w-0 flex-1 ${
                      isCompleted ? "bg-gray-950" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const CreateStrategyModal: FC<CreateStrategyModalProps> = ({ children }) => {
  const [open, setOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState<StepNumber>(1);

  const { data: prompts = [] } = useGetStrategyPrompts();
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
      onSubmit: step1Schema,
    },
    onSubmit: () => {
      setCurrentStep(2);
    },
  });

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
      onSubmit: step2Schema,
    },
    onSubmit: () => {
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
      symbols: TRADING_SYMBOLS,
      template_id: prompts.length > 0 ? prompts[0].id : "",
    },
    validators: {
      onSubmit: step3Schema,
    },
    onSubmit: async ({ value }) => {
      const payload = {
        llm_model_config: form1.state.values,
        exchange_config: form2.state.values,
        trading_config: value,
      };

      await createStrategy(payload);
      resetAll();
    },
  });

  const resetAll = () => {
    setCurrentStep(1);
    form1.reset();
    form2.reset();
    form3.reset();
    setOpen(false);
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as StepNumber);
    }
  };

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

          <StepIndicator currentStep={currentStep} />
        </DialogTitle>

        {/* Form content with scroll */}
        <ScrollContainer className="px-1 py-2">
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
        </ScrollContainer>

        {/* Footer buttons */}
        <div className="mt-auto flex gap-6">
          <Button
            type="button"
            variant="outline"
            onClick={currentStep === 1 ? resetAll : handleBack}
            className="flex-1 border-gray-100 py-4 font-semibold text-base"
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
            className="flex-1 py-4 font-semibold text-base text-white hover:bg-gray-800"
          >
            {isCreatingStrategy && <Spinner />}{" "}
            {currentStep === 3 ? "Confirm" : "Next"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default memo(CreateStrategyModal);
