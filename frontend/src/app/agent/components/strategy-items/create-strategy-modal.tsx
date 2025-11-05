import { useForm } from "@tanstack/react-form";
import { Check, X } from "lucide-react";
import type { FC } from "react";
import { useState } from "react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";

interface CreateStrategyModalProps {
  trigger?: React.ReactNode;
}

type StepNumber = 1 | 2 | 3;

// Form validation schema
const formSchema = z.object({
  // Step 1: AI Model Config
  modelProvider: z.string().min(1, "Model platform is required"),
  modelId: z.string().min(1, "Model selection is required"),
  modelApiKey: z.string().min(1, "API key is required"),
  // Step 2: Exchange Config
  exchangeId: z.string().min(1, "Exchange is required"),
  tradingMode: z.enum(["live", "virtual"]),
  exchangeApiKey: z.string(),
  exchangeSecretKey: z.string(),
  // Step 3: Trading Config
  strategyName: z.string().min(1, "Strategy name is required"),
  initialCapital: z.number().min(0, "Initial capital must be positive"),
  maxLeverage: z.number().min(1, "Leverage must be at least 1"),
  symbols: z.string().min(1, "At least one symbol is required"),
  templateId: z.string().min(1, "Template selection is required"),
  customPrompt: z.string(),
});

const STEPS = [
  { number: 1 as const, title: "AI Models" },
  { number: 2 as const, title: "Exchanges" },
  { number: 3 as const, title: "Trading strategy" },
];

// Custom Step Indicator Component
const StepIndicator: FC<{ currentStep: StepNumber }> = ({ currentStep }) => {
  return (
    <div className="flex items-start">
      {STEPS.map((step, index) => {
        const isCompleted = step.number < currentStep;
        const isCurrent = step.number === currentStep;

        return (
          <div key={step.number} className="flex min-w-0 flex-1 items-start">
            <div className="flex w-full items-start gap-4 px-0 py-1">
              {/* Step circle */}
              <div className="relative flex size-6 shrink-0 items-center justify-center">
                {isCompleted ? (
                  <div className="flex size-6 items-center justify-center rounded-full bg-[#030712]">
                    <Check className="size-3 text-white" />
                  </div>
                ) : (
                  <>
                    <div
                      className={`absolute inset-0 rounded-full border-2 ${
                        isCurrent
                          ? "border-[#0052D9] bg-[#030712]"
                          : "border-black"
                      }`}
                    />
                    <span
                      className={`relative font-semibold text-base ${
                        isCurrent ? "text-white" : "text-black/40"
                      }`}
                    >
                      {step.number}
                    </span>
                  </>
                )}
              </div>

              {/* Title and divider */}
              <div className="flex min-w-0 flex-1 items-center gap-4 overflow-hidden pr-4">
                <p
                  className={`shrink-0 whitespace-nowrap text-base ${
                    isCompleted || isCurrent
                      ? "font-normal text-black/90"
                      : "font-normal text-black/40"
                  }`}
                >
                  {step.title}
                </p>
                {index < STEPS.length - 1 && (
                  <div
                    className={`h-0.5 min-w-0 flex-1 ${
                      isCompleted ? "bg-gray-950" : "bg-[gainsboro]"
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

export const CreateStrategyModal: FC<CreateStrategyModalProps> = ({
  trigger,
}) => {
  const [open, setOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState<StepNumber>(1);

  const form = useForm({
    defaultValues: {
      modelProvider: "openrouter",
      modelId: "deepseek-ai/DeepSeek-V3.1-Terminus",
      modelApiKey: "",
      exchangeId: "okx",
      tradingMode: "live" as "live" | "virtual",
      exchangeApiKey: "",
      exchangeSecretKey: "",
      strategyName: "",
      initialCapital: 1000,
      maxLeverage: 8,
      symbols: "",
      templateId: "default",
      customPrompt: "",
    },
    validators: {
      onSubmit: formSchema,
    },
    onSubmit: async ({ value }) => {
      // Convert flat form to nested structure
      const payload = {
        modelConfig: {
          provider: value.modelProvider,
          modelId: value.modelId,
          apiKey: value.modelApiKey,
        },
        exchangeConfig: {
          exchangeId: value.exchangeId,
          tradingMode: value.tradingMode,
          apiKey: value.exchangeApiKey,
          secretKey: value.exchangeSecretKey,
        },
        tradingConfig: {
          strategyName: value.strategyName,
          initialCapital: value.initialCapital,
          maxLeverage: value.maxLeverage,
          symbols: value.symbols
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          templateId: value.templateId,
          customPrompt: value.customPrompt,
        },
      };
      console.log("Form submitted:", payload);
      setOpen(false);
      setCurrentStep(1);
    },
  });

  const handleNext = () => {
    if (currentStep < 3) {
      setCurrentStep((prev) => (prev + 1) as StepNumber);
    } else {
      form.handleSubmit();
    }
  };

  const handleCancel = () => {
    setOpen(false);
    setCurrentStep(1);
    form.reset();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" className="gap-3">
            Add trading strategy
          </Button>
        )}
      </DialogTrigger>

      <DialogContent
        className="flex max-h-[90vh] max-w-2xl flex-col rounded-[24px] p-10"
        showCloseButton={false}
      >
        {/* Header */}
        <div className="flex shrink-0 flex-col gap-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg leading-[26px]">
              Add trading strategy
            </h2>
            <button
              type="button"
              onClick={handleCancel}
              className="flex size-6 shrink-0 items-center justify-center"
            >
              <X className="size-4 text-gray-400" />
            </button>
          </div>

          {/* Step indicator */}
          <StepIndicator currentStep={currentStep} />
        </div>

        {/* Form content with scroll */}
        <ScrollContainer className="flex-1 overflow-y-auto">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleNext();
            }}
            className="flex flex-col gap-6 py-2"
          >
            {/* Step 1: AI Models */}
            {currentStep === 1 && (
              <FieldGroup className="gap-6">
                <form.Field name="modelProvider">
                  {(field) => {
                    const isInvalid =
                      field.state.meta.isTouched &&
                      field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel className="font-medium text-base text-gray-950">
                          Model Platform
                        </FieldLabel>
                        <Select
                          value={field.state.value}
                          onValueChange={field.handleChange}
                        >
                          <SelectTrigger className="h-[58px] justify-between rounded-[10px] border-gray-200 px-4">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openrouter">
                              Openrouter
                            </SelectItem>
                            <SelectItem value="openai">OpenAI</SelectItem>
                            <SelectItem value="anthropic">Anthropic</SelectItem>
                          </SelectContent>
                        </Select>
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    );
                  }}
                </form.Field>

                <form.Field name="modelId">
                  {(field) => {
                    const isInvalid =
                      field.state.meta.isTouched &&
                      field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel className="font-medium text-base text-gray-950">
                          Select Model
                        </FieldLabel>
                        <Select
                          value={field.state.value}
                          onValueChange={field.handleChange}
                        >
                          <SelectTrigger className="h-[58px] justify-between rounded-[10px] border-gray-200 px-4">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="deepseek-ai/DeepSeek-V3.1-Terminus">
                              Deepseek-ai/DeepSeek-V3.1-Terminus
                            </SelectItem>
                            <SelectItem value="gpt-4">GPT-4</SelectItem>
                            <SelectItem value="claude-3">Claude 3</SelectItem>
                          </SelectContent>
                        </Select>
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    );
                  }}
                </form.Field>

                <form.Field name="modelApiKey">
                  {(field) => {
                    const isInvalid =
                      field.state.meta.isTouched &&
                      field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel className="font-medium text-base text-gray-950">
                          API key
                        </FieldLabel>
                        <Input
                          value={field.state.value}
                          onChange={(e) => field.handleChange(e.target.value)}
                          onBlur={field.handleBlur}
                          placeholder="Enter API Key"
                        />
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    );
                  }}
                </form.Field>
              </FieldGroup>
            )}

            {/* Step 2: Exchanges */}
            {currentStep === 2 && (
              <FieldGroup className="gap-6">
                <form.Field name="tradingMode">
                  {(field) => (
                    <Field>
                      <FieldLabel className="font-medium text-base text-gray-950">
                        Transaction Type
                      </FieldLabel>
                      <RadioGroup
                        value={field.state.value}
                        onValueChange={(value) =>
                          field.handleChange(value as "live" | "virtual")
                        }
                        className="flex items-center gap-6"
                      >
                        <div className="flex items-center gap-2">
                          <RadioGroupItem value="live" id="live" />
                          <Label htmlFor="live" className="text-sm">
                            Live Trading
                          </Label>
                        </div>
                        <div className="flex items-center gap-2">
                          <RadioGroupItem value="virtual" id="virtual" />
                          <Label htmlFor="virtual" className="text-sm">
                            Virtual Trading
                          </Label>
                        </div>
                      </RadioGroup>
                    </Field>
                  )}
                </form.Field>

                <form.Field name="exchangeId">
                  {(field) => {
                    const isInvalid =
                      field.state.meta.isTouched &&
                      field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel className="font-medium text-base text-gray-950">
                          Select Exchange
                        </FieldLabel>
                        <Select
                          value={field.state.value}
                          onValueChange={field.handleChange}
                        >
                          <SelectTrigger className="h-[58px] justify-between rounded-[10px] border-gray-200 px-4">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="okx">OKX</SelectItem>
                            <SelectItem value="binance">Binance</SelectItem>
                            <SelectItem value="coinbase">Coinbase</SelectItem>
                          </SelectContent>
                        </Select>
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    );
                  }}
                </form.Field>

                <form.Field name="exchangeApiKey">
                  {(field) => (
                    <Field>
                      <FieldLabel className="font-medium text-base text-gray-950">
                        API key
                      </FieldLabel>
                      <Input
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        placeholder="Enter API Key"
                      />
                    </Field>
                  )}
                </form.Field>

                <form.Field name="exchangeSecretKey">
                  {(field) => (
                    <Field>
                      <FieldLabel className="font-medium text-base text-gray-950">
                        Secret Key
                      </FieldLabel>
                      <Input
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        placeholder="Enter Secret Key"
                      />
                    </Field>
                  )}
                </form.Field>
              </FieldGroup>
            )}

            {/* Step 3: Trading Strategy */}
            {currentStep === 3 && (
              <FieldGroup className="gap-6">
                <form.Field name="strategyName">
                  {(field) => {
                    const isInvalid =
                      field.state.meta.isTouched &&
                      field.state.meta.errors.length > 0;
                    return (
                      <Field data-invalid={isInvalid}>
                        <FieldLabel className="font-medium text-base text-gray-950">
                          Strategy Name
                        </FieldLabel>
                        <Input
                          value={field.state.value}
                          onChange={(e) => field.handleChange(e.target.value)}
                          onBlur={field.handleBlur}
                          placeholder="Enter strategy name"
                        />
                        {isInvalid && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    );
                  }}
                </form.Field>

                {/* Transaction Configuration Section */}
                <div className="flex flex-col gap-6">
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-1 rounded-[1px] bg-black" />
                    <h3 className="font-semibold text-lg leading-[26px]">
                      Transaction configuration
                    </h3>
                  </div>

                  <div className="flex flex-col gap-4">
                    <div className="flex gap-4">
                      <form.Field name="initialCapital">
                        {(field) => {
                          const isInvalid =
                            field.state.meta.isTouched &&
                            field.state.meta.errors.length > 0;
                          return (
                            <Field data-invalid={isInvalid} className="flex-1">
                              <FieldLabel className="font-medium text-base text-gray-950">
                                Initial Capital
                              </FieldLabel>
                              <Input
                                type="number"
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(Number(e.target.value))
                                }
                                onBlur={field.handleBlur}
                              />
                              {isInvalid && (
                                <FieldError errors={field.state.meta.errors} />
                              )}
                            </Field>
                          );
                        }}
                      </form.Field>

                      <form.Field name="maxLeverage">
                        {(field) => {
                          const isInvalid =
                            field.state.meta.isTouched &&
                            field.state.meta.errors.length > 0;
                          return (
                            <Field data-invalid={isInvalid} className="flex-1">
                              <FieldLabel className="font-medium text-base text-gray-950">
                                Max Leverage
                              </FieldLabel>
                              <Input
                                type="number"
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(Number(e.target.value))
                                }
                                onBlur={field.handleBlur}
                              />
                              {isInvalid && (
                                <FieldError errors={field.state.meta.errors} />
                              )}
                            </Field>
                          );
                        }}
                      </form.Field>
                    </div>

                    <form.Field name="symbols">
                      {(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          field.state.meta.errors.length > 0;
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel className="font-medium text-base text-gray-950">
                              Trading Symbols
                            </FieldLabel>
                            <Input
                              value={field.state.value}
                              onChange={(e) =>
                                field.handleChange(e.target.value)
                              }
                              onBlur={field.handleBlur}
                              placeholder="BTC, ETH, SOL, DOGE, XRP"
                            />
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        );
                      }}
                    </form.Field>
                  </div>
                </div>

                {/* Trading Strategy Prompt Section */}
                <div className="flex flex-col gap-6">
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-1 rounded-[1px] bg-black" />
                    <h3 className="font-semibold text-lg leading-[26px]">
                      Trading strategy prompt
                    </h3>
                  </div>

                  <div className="flex flex-col gap-4">
                    <form.Field name="templateId">
                      {(field) => {
                        const isInvalid =
                          field.state.meta.isTouched &&
                          field.state.meta.errors.length > 0;
                        return (
                          <Field data-invalid={isInvalid}>
                            <FieldLabel className="font-medium text-base text-gray-950">
                              System Prompt Template
                            </FieldLabel>
                            <Select
                              value={field.state.value}
                              onValueChange={field.handleChange}
                            >
                              <SelectTrigger className="h-[58px] justify-between rounded-[10px] border-gray-200 px-4">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="default">Default</SelectItem>
                                <SelectItem value="aggressive">
                                  Aggressive
                                </SelectItem>
                                <SelectItem value="conservative">
                                  Conservative
                                </SelectItem>
                              </SelectContent>
                            </Select>
                            {isInvalid && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        );
                      }}
                    </form.Field>

                    <form.Field name="customPrompt">
                      {(field) => (
                        <Field>
                          <FieldLabel className="font-medium text-base text-gray-950">
                            Custom Prompt
                          </FieldLabel>
                          <Textarea
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            onBlur={field.handleBlur}
                            placeholder="Additional custom prompt..."
                            className="min-h-[117px] rounded-[10px] border-gray-200 px-4 py-4 text-base placeholder:text-gray-400"
                          />
                        </Field>
                      )}
                    </form.Field>
                  </div>
                </div>
              </FieldGroup>
            )}
          </form>
        </ScrollContainer>

        {/* Footer buttons */}
        <div className="mt-6 flex shrink-0 gap-[25px]">
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            className="flex-1 rounded-[10px] border-gray-100 py-4 font-semibold text-base leading-[22px]"
          >
            Cancel
          </Button>
          <Button
            onClick={handleNext}
            className="flex-1 rounded-[10px] bg-gray-950 py-4 font-semibold text-base text-white leading-[22px] hover:bg-gray-800"
          >
            {currentStep === 3 ? "Confirm" : "Next"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
