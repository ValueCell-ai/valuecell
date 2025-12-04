import { MultiSelect } from "@valuecell/multi-select";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { SelectItem } from "@/components/ui/select";
import { TRADING_SYMBOLS } from "@/constants/agent";
import { withForm } from "@/hooks/use-form";
import type { Strategy } from "@/types/strategy";

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
              placeholder="e.g. 300"
            />
          )}
        </form.AppField>

        <form.Subscribe selector={(state) => state.values.strategy_type}>
          {(strategyType) => {
            return (
              <form.Field name="symbols">
                {(field) => (
                  <Field>
                    <FieldLabel className="font-medium text-base text-gray-950">
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
                      <FieldLabel className="font-medium text-base text-gray-950">
                        System Prompt Template
                      </FieldLabel>
                      <div className="text-gray-500 text-sm">
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
      </FieldGroup>
    );
  },
});
