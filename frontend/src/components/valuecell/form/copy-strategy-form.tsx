import { MultiSelect } from "@valuecell/multi-select";
import { Eye, Plus } from "lucide-react";
import { useCreateStrategyPrompt } from "@/api/strategy";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { SelectItem } from "@/components/ui/select";
import { TRADING_SYMBOLS } from "@/constants/agent";
import { withForm } from "@/hooks/use-form";
import type {
  DynamicStrategyConfig,
  Strategy,
  StrategyPrompt,
} from "@/types/strategy";
import { DynamicStrategyConfigForm } from "./dynamic-strategy-config";
import NewPromptModal from "../modals/new-prompt-modal";
import ViewStrategyModal from "../modals/view-strategy-modal";

export const CopyStrategyForm = withForm({
  defaultValues: {
    strategy_type: "" as Strategy["strategy_type"],
    strategy_name: "",
    initial_capital: 1000,
    max_leverage: 2,
    decide_interval: 60,
    symbols: TRADING_SYMBOLS,
    prompt_name: "",
    prompt: "",
    decide_interval: 60, // Default: 60 seconds (1 minute)
    enable_dynamic_strategy: false,
    dynamicConfig: undefined as DynamicStrategyConfig | undefined,
  },
  props: {
    tradingMode: "live" as "live" | "virtual",
  },
  render({ form, tradingMode }) {
    return (
      <FieldGroup className="gap-6">
        <form.AppField
          listeners={{
            onChange: ({ value }: { value: Strategy["strategy_type"] }) => {
              if (value === "GridStrategy") {
                form.setFieldValue("symbols", [TRADING_SYMBOLS[0]]);
              } else {
                form.setFieldValue("symbols", TRADING_SYMBOLS);
              }
            },
          }}
          name="strategy_type"
        >
          {(field) => (
            <field.SelectField label="Strategy Type">
              <SelectItem value="PromptBasedStrategy">
                Prompt Based Strategy
              </SelectItem>
              <SelectItem value="GridStrategy">Grid Strategy</SelectItem>
            </field.SelectField>
          )}
        </form.AppField>

        <form.AppField name="strategy_name">
          {(field) => (
            <field.TextField
              label="Strategy Name"
              placeholder="Enter strategy name"
            />
          )}
        </form.AppField>

        <FieldGroup className="flex flex-row gap-4">
          {tradingMode === "virtual" && (
            <form.AppField name="initial_capital">
              {(field) => (
                <field.NumberField
                  className="flex-1"
                  label="Initial Capital"
                  placeholder="Enter Initial Capital"
                />
              )}
            </form.AppField>
          )}

          <form.AppField name="max_leverage">
            {(field) => (
              <field.NumberField
                className="flex-1"
                label="Max Leverage"
                placeholder="Max Leverage"
              />
            )}
          </form.AppField>
        </FieldGroup>

        <form.AppField name="decide_interval">
          {(field) => (
            <field.NumberField
              label="Decision Interval (seconds)"
              placeholder="Enter decision interval in seconds"
              description="Time between decision cycles. Default: 60 seconds (1 minute). Minimum: 10 seconds, Maximum: 3600 seconds (1 hour)."
            />
          )}
        </form.AppField>

        <form.Subscribe selector={(state) => state.values.strategy_type}>
          {(strategyType) => {
            return (
              <form.Field name="symbols">
                {(field) => (
                  <Field>
                    <FieldLabel className="font-medium text-base text-foreground">
                      Trading Symbols
                    </FieldLabel>
                    <MultiSelect
                      maxSelected={
                        strategyType === "GridStrategy" ? 1 : undefined
                      }
                      options={TRADING_SYMBOLS}
                      value={field.state.value}
                      onValueChange={(value) => field.handleChange(value)}
                      placeholder="Select trading symbols..."
                      searchPlaceholder="Search or add symbols..."
                      emptyText="No symbols found."
                      maxDisplayed={5}
                      creatable
                    />
                    <FieldError errors={field.state.meta.errors} />
                  </Field>
                )}
              </form.Field>
            );
          }}
        </form.Subscribe>

        <form.Subscribe selector={(state) => state.values.strategy_type}>
          {(strategyType) => {
            return (
              strategyType === "PromptBasedStrategy" && (
                <form.Field name="prompt">
                  {(field) => (
                    <Field>
                      <FieldLabel className="font-medium text-base text-foreground">
                        System Prompt Template
                      </FieldLabel>
                      <div className="text-muted-foreground text-sm">
                        {field.state.value}
                      </div>
                      <FieldError errors={field.state.meta.errors} />
                    </Field>
                  )}
                </form.Field>
              )
            );
          }}
        </form.Subscribe>

        {/* Dynamic Strategy Configuration */}
        <form.AppField name="enable_dynamic_strategy">
          {(field) => (
            <Field>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="enable_dynamic_strategy"
                  checked={field.state.value}
                  onCheckedChange={(checked) => {
                    field.handleChange(checked);
                    if (checked && !form.getFieldValue("dynamicConfig")) {
                      form.setFieldValue("dynamicConfig", {
                        baseStrategy: ["TREND", "GRID", "BREAKOUT", "ARBITRAGE"],
                        switchMode: "SCORE",
                        scoreWeights: {
                          volatility: 0.25,
                          trendStrength: 0.25,
                          volumeRatio: 0.25,
                          marketSentiment: 0.25,
                        },
                        riskMode: "NEUTRAL",
                      });
                    } else if (!checked) {
                      form.setFieldValue("dynamicConfig", undefined);
                    }
                  }}
                />
                <FieldLabel
                  htmlFor="enable_dynamic_strategy"
                  className="text-base font-medium cursor-pointer"
                >
                  启用动态策略评分选择器
                </FieldLabel>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                根据实时市场条件自动选择最佳策略
              </p>
            </Field>
          )}
        </form.AppField>

        <form.Subscribe
          selector={(state) => state.values.enable_dynamic_strategy}
        >
          {(enabled) => {
            if (!enabled) return null;

            const dynamicConfig = form.getFieldValue("dynamicConfig");
            if (!dynamicConfig) return null;

            return (
              <div className="mt-4">
                <DynamicStrategyConfigForm
                  value={dynamicConfig}
                  onChange={(config) => {
                    form.setFieldValue("dynamicConfig", config);
                  }}
                />
              </div>
            );
          }}
        </form.Subscribe>
      </FieldGroup>
    );
  },
});
