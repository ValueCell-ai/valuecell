import { useForm } from "@tanstack/react-form";
import { MultiSelect } from "@valuecell/multi-select";
import { Check, X } from "lucide-react";
import type { FC } from "react";
import { memo, useState } from "react";
import { z } from "zod";
import { useCreateStrategy, useGetStrategyApiKey } from "@/api/strategy";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import {
  MODEL_PROVIDER_MAP,
  MODEL_PROVIDERS,
  TRADING_SYMBOLS,
} from "@/constants/agent";

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
const step2Schema = z
  .object({
    trading_mode: z.enum(["live", "virtual"]),
    exchange_id: z.string(),
    api_key: z.string(),
    secret_key: z.string(),
    passphrase: z.string(), // Required string, but can be empty for non-OKX exchanges
  })
  .superRefine((data, ctx) => {
    // Only validate exchange credentials when live trading is selected
    if (data.trading_mode === "live") {
      const fields = [
        {
          name: "exchange_id",
          label: "Exchange",
          value: data.exchange_id,
        },
        {
          name: "api_key",
          label: "API key",
          value: data.api_key,
        },
        {
          name: "secret_key",
          label: "Secret key",
          value: data.secret_key,
        },
      ];

      for (const field of fields) {
        if (!field.value?.trim()) {
          ctx.addIssue({
            code: "custom",
            message: `${field.label} is required for live trading`,
            path: [field.name],
          });
        }
      }

      // OKX requires passphrase
      if (data.exchange_id === "okx" && !data.passphrase?.trim()) {
        ctx.addIssue({
          code: "custom",
          message: "Password is required for OKX",
          path: ["passphrase"],
        });
      }
    }
    // Virtual trading mode: no validation needed for exchange fields
  });

// Step 3 Schema: Trading Strategy
const step3Schema = z.object({
  strategy_name: z.string().min(1, "Strategy name is required"),
  initial_capital: z.number().min(0, "Initial capital must be positive"),
  max_leverage: z.number().min(1, "Leverage must be at least 1"),
  symbols: z.array(z.string()).min(1, "At least one symbol is required"),
  template_id: z.string().min(1, "Template selection is required"),
  custom_prompt: z.string(),
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
            isCurrent ? "border-gray-950 bg-gray-700" : "border-black/40"
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
      {STEPS.map((step, index) => {
        const { isCompleted, isCurrent, isActive } = getStepState(step.number);
        const isLastStep = index === STEPS.length - 1;

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

                {!isLastStep && (
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
  const { mutateAsync: createStrategy } = useCreateStrategy();
  const { data: llmConfigs } = useGetStrategyApiKey();

  // Step 1 Form: AI Models
  const form1 = useForm({
    defaultValues: {
      provider: "openrouter",
      model_id: MODEL_PROVIDER_MAP.openrouter[0],
      api_key:
        llmConfigs?.find((config) => config.provider === "openrouter")
          ?.api_key || "",
    },
    validators: {
      onSubmit: step1Schema,
    },
    onSubmit: () => {
      setCurrentStep(2);
    },
  });

  // Step 2 Form: Exchanges
  const form2 = useForm({
    defaultValues: {
      trading_mode: "live" as "live" | "virtual",
      exchange_id: "okx",
      api_key: "",
      secret_key: "",
      passphrase: "",
    },
    validators: {
      onSubmit: step2Schema,
    },
    onSubmit: () => {
      setCurrentStep(3);
    },
  });

  // Step 3 Form: Trading Strategy
  const form3 = useForm({
    defaultValues: {
      strategy_name: "",
      initial_capital: 1000,
      max_leverage: 8,
      symbols: TRADING_SYMBOLS,
      template_id: "default",
      custom_prompt: "",
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
      setOpen(false);
      resetAll();
    },
  });

  const resetAll = () => {
    setCurrentStep(1);
    form1.reset();
    form2.reset();
    form3.reset();
  };

  const handleCancel = () => {
    setOpen(false);
    resetAll();
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as StepNumber);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children || (
          <Button variant="outline" className="gap-3">
            Add trading strategy
          </Button>
        )}
      </DialogTrigger>

      <DialogContent
        className="flex max-h-[90vh] min-h-96 flex-col"
        showCloseButton={false}
        aria-describedby={undefined}
      >
        <DialogTitle className="flex flex-col gap-4 px-1">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">Add trading strategy</h2>
            <Button variant="ghost" size="icon" onClick={handleCancel}>
              <X />
            </Button>
          </div>

          <StepIndicator currentStep={currentStep} />
        </DialogTitle>

        {/* Form content with scroll */}
        <ScrollContainer>
          <div className="px-1 py-2">
            {/* Step 1: AI Models */}
            {currentStep === 1 && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  form1.handleSubmit();
                }}
              >
                <FieldGroup className="gap-6">
                  <form1.Field name="provider">
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
                            onValueChange={(value) => {
                              field.handleChange(value);
                              form1.setFieldValue(
                                "model_id",
                                MODEL_PROVIDER_MAP[
                                  value as keyof typeof MODEL_PROVIDER_MAP
                                ][0],
                              );
                              const apikey = llmConfigs?.find(
                                (config) => config.provider === value,
                              )?.api_key;
                              if (apikey) {
                                form1.setFieldValue("api_key", apikey);
                              }
                            }}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {MODEL_PROVIDERS.map((provider) => (
                                <SelectItem key={provider} value={provider}>
                                  {provider}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {isInvalid && (
                            <FieldError errors={field.state.meta.errors} />
                          )}
                        </Field>
                      );
                    }}
                  </form1.Field>

                  <form1.Field name="model_id">
                    {(field) => {
                      const isInvalid =
                        field.state.meta.isTouched &&
                        field.state.meta.errors.length > 0;
                      const currentProvider = form1.state.values
                        .provider as keyof typeof MODEL_PROVIDER_MAP;
                      const availableModels =
                        MODEL_PROVIDER_MAP[currentProvider] || [];

                      return (
                        <Field key={currentProvider} data-invalid={isInvalid}>
                          <FieldLabel className="font-medium text-base text-gray-950">
                            Select Model
                          </FieldLabel>
                          <Select
                            value={field.state.value}
                            onValueChange={field.handleChange}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {availableModels.length > 0 ? (
                                availableModels.map((model) => (
                                  <SelectItem key={model} value={model}>
                                    {model}
                                  </SelectItem>
                                ))
                              ) : (
                                <SelectItem value="" disabled>
                                  No models available
                                </SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                          {isInvalid && (
                            <FieldError errors={field.state.meta.errors} />
                          )}
                        </Field>
                      );
                    }}
                  </form1.Field>

                  <form1.Field key={form1.state.values.provider} name="api_key">
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
                  </form1.Field>
                </FieldGroup>
              </form>
            )}

            {/* Step 2: Exchanges */}
            {currentStep === 2 && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  form2.handleSubmit();
                }}
              >
                <FieldGroup className="gap-6">
                  <form2.Field name="trading_mode">
                    {(field) => {
                      const isLiveTrading = field.state.value === "live";

                      return (
                        <>
                          <Field>
                            <FieldLabel className="font-medium text-base text-gray-950">
                              Transaction Type
                            </FieldLabel>
                            <RadioGroup
                              value={field.state.value}
                              onValueChange={(value) => {
                                const newMode = value as "live" | "virtual";
                                form2.reset();

                                field.handleChange(newMode);
                              }}
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

                          {isLiveTrading && (
                            <>
                              <form2.Field name="exchange_id">
                                {(field) => (
                                  <Field>
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
                                        <SelectItem value="binance">
                                          Binance
                                        </SelectItem>
                                      </SelectContent>
                                    </Select>
                                    {field.state.meta.errors.length > 0 && (
                                      <FieldError
                                        errors={field.state.meta.errors}
                                      />
                                    )}
                                  </Field>
                                )}
                              </form2.Field>

                              <form2.Field name="api_key">
                                {(field) => (
                                  <Field>
                                    <FieldLabel className="font-medium text-base text-gray-950">
                                      API key
                                    </FieldLabel>
                                    <Input
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(e.target.value)
                                      }
                                      onBlur={field.handleBlur}
                                      placeholder="Enter API Key"
                                    />
                                    {field.state.meta.errors.length > 0 && (
                                      <FieldError
                                        errors={field.state.meta.errors}
                                      />
                                    )}
                                  </Field>
                                )}
                              </form2.Field>

                              <form2.Field name="secret_key">
                                {(field) => (
                                  <Field>
                                    <FieldLabel className="font-medium text-base text-gray-950">
                                      Secret Key
                                    </FieldLabel>
                                    <Input
                                      value={field.state.value}
                                      onChange={(e) =>
                                        field.handleChange(e.target.value)
                                      }
                                      onBlur={field.handleBlur}
                                      placeholder="Enter Secret Key"
                                    />
                                    {field.state.meta.errors.length > 0 && (
                                      <FieldError
                                        errors={field.state.meta.errors}
                                      />
                                    )}
                                  </Field>
                                )}
                              </form2.Field>

                              {/* Password field - only shown for OKX */}
                              <form2.Field name="exchange_id">
                                {(exchangeField) =>
                                  exchangeField.state.value === "okx" ? (
                                    <form2.Field name="passphrase">
                                      {(field) => (
                                        <Field>
                                          <FieldLabel className="font-medium text-base text-gray-950">
                                            Password
                                          </FieldLabel>
                                          <Input
                                            value={field.state.value}
                                            onChange={(e) =>
                                              field.handleChange(e.target.value)
                                            }
                                            onBlur={field.handleBlur}
                                            placeholder="Enter Password (Required for OKX)"
                                          />
                                          {field.state.meta.errors.length >
                                            0 && (
                                            <FieldError
                                              errors={field.state.meta.errors}
                                            />
                                          )}
                                        </Field>
                                      )}
                                    </form2.Field>
                                  ) : null
                                }
                              </form2.Field>
                            </>
                          )}
                        </>
                      );
                    }}
                  </form2.Field>
                </FieldGroup>
              </form>
            )}

            {/* Step 3: Trading Strategy */}
            {currentStep === 3 && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  form3.handleSubmit();
                }}
              >
                <FieldGroup className="gap-6">
                  <form3.Field name="strategy_name">
                    {(field) => (
                      <Field>
                        <FieldLabel className="font-medium text-base text-gray-950">
                          Strategy Name
                        </FieldLabel>
                        <Input
                          value={field.state.value}
                          onChange={(e) => field.handleChange(e.target.value)}
                          onBlur={field.handleBlur}
                          placeholder="Enter strategy name"
                        />
                        {field.state.meta.errors.length > 0 && (
                          <FieldError errors={field.state.meta.errors} />
                        )}
                      </Field>
                    )}
                  </form3.Field>

                  {/* Transaction Configuration */}
                  <div className="flex flex-col gap-6">
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-1 rounded-[1px] bg-black" />
                      <h3 className="font-semibold text-lg leading-[26px]">
                        Transaction configuration
                      </h3>
                    </div>

                    <div className="flex flex-col gap-4">
                      <div className="flex gap-4">
                        <form3.Field name="initial_capital">
                          {(field) => (
                            <Field className="flex-1">
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
                              {field.state.meta.errors.length > 0 && (
                                <FieldError errors={field.state.meta.errors} />
                              )}
                            </Field>
                          )}
                        </form3.Field>

                        <form3.Field name="max_leverage">
                          {(field) => (
                            <Field className="flex-1">
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
                              {field.state.meta.errors.length > 0 && (
                                <FieldError errors={field.state.meta.errors} />
                              )}
                            </Field>
                          )}
                        </form3.Field>
                      </div>

                      <form3.Field name="symbols">
                        {(field) => (
                          <Field>
                            <FieldLabel className="font-medium text-base text-gray-950">
                              Trading Symbols
                            </FieldLabel>
                            <MultiSelect
                              options={TRADING_SYMBOLS}
                              value={field.state.value}
                              onValueChange={(value) =>
                                field.handleChange(value)
                              }
                              placeholder="Select trading symbols..."
                              searchPlaceholder="Search symbols..."
                              emptyText="No symbols found."
                              maxDisplayed={5}
                              className="h-[58px] rounded-[10px] border-gray-200"
                            />
                            {field.state.meta.errors.length > 0 && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        )}
                      </form3.Field>
                    </div>
                  </div>

                  {/* Trading Strategy Prompt */}
                  {/* <div className="flex flex-col gap-6">
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-1 rounded-[1px] bg-black" />
                      <h3 className="font-semibold text-lg leading-[26px]">
                        Trading strategy prompt
                      </h3>
                    </div>

                    <div className="flex flex-col gap-4">
                      <form3.Field name="template_id">
                        {(field) => (
                          <Field>
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
                            {field.state.meta.errors.length > 0 && (
                              <FieldError errors={field.state.meta.errors} />
                            )}
                          </Field>
                        )}
                      </form3.Field>

                      <form3.Field name="custom_prompt">
                        {(field) => (
                          <Field>
                            <FieldLabel className="font-medium text-base text-gray-950">
                              Custom Prompt
                            </FieldLabel>
                            <Textarea
                              value={field.state.value}
                              onChange={(e) =>
                                field.handleChange(e.target.value)
                              }
                              onBlur={field.handleBlur}
                              placeholder="Additional custom prompt..."
                              className="min-h-[117px] rounded-[10px] border-gray-200 px-4 py-4 text-base placeholder:text-gray-400"
                            />
                          </Field>
                        )}
                      </form3.Field>
                    </div>
                  </div> */}
                </FieldGroup>
              </form>
            )}
          </div>
        </ScrollContainer>

        {/* Footer buttons */}
        <div className="mt-auto flex gap-6">
          <Button
            type="button"
            variant="outline"
            onClick={currentStep === 1 ? handleCancel : handleBack}
            className="flex-1 border-gray-100 py-4 font-semibold text-base"
          >
            {currentStep === 1 ? "Cancel" : "Back"}
          </Button>
          <Button
            type="button"
            onClick={() => {
              if (currentStep === 1) {
                form1.handleSubmit();
              } else if (currentStep === 2) {
                form2.handleSubmit();
              } else {
                form3.handleSubmit();
              }
            }}
            className="flex-1 py-4 font-semibold text-base text-white hover:bg-gray-800"
          >
            {currentStep === 3 ? "Confirm" : "Next"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default memo(CreateStrategyModal);
