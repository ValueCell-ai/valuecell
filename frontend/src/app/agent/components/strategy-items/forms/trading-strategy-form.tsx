import { MultiSelect } from "@valuecell/multi-select";
import { Eye, Plus } from "lucide-react";
import { useCreateStrategyPrompt } from "@/api/strategy";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TRADING_SYMBOLS } from "@/constants/agent";
import { withForm } from "@/hooks/use-form";
import type { Strategy, StrategyPrompt } from "@/types/strategy";
import NewPromptModal from "../modals/new-prompt-modal";
import ViewStrategyModal from "../modals/view-strategy-modal";

export const TradingStrategyForm = withForm({
  defaultValues: {
    strategy_type: "" as Strategy["strategy_type"],
    strategy_name: "",
    initial_capital: 1000,
    max_leverage: 2,
    decide_interval: 60,
    symbols: TRADING_SYMBOLS,
    template_id: "",
  },
  props: {
    prompts: [] as StrategyPrompt[],
    tradingMode: "live" as "live" | "virtual",
  },
  render({ form, prompts, tradingMode }) {
    const { mutateAsync: createStrategyPrompt } = useCreateStrategyPrompt();

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
                <form.Field name="template_id">
                  {(field) => (
                    <Field>
                      <FieldLabel className="font-medium text-base text-gray-950">
                        System Prompt Template
                      </FieldLabel>
                      <div className="flex items-center gap-3">
                        <Select
                          value={field.state.value}
                          onValueChange={(value) => {
                            field.handleChange(value);
                          }}
                        >
                          <SelectTrigger className="flex-1">
                            <SelectValue />
                          </SelectTrigger>

                          <SelectContent>
                            {prompts.length > 0 &&
                              prompts.map((prompt) => (
                                <SelectItem key={prompt.id} value={prompt.id}>
                                  {prompt.name}
                                </SelectItem>
                              ))}
                            <NewPromptModal
                              onSave={async (value) => {
                                const { data: prompt } =
                                  await createStrategyPrompt(value);
                                form.setFieldValue("template_id", prompt.id);
                              }}
                            >
                              <Button
                                className="w-full"
                                type="button"
                                variant="outline"
                              >
                                <Plus />
                                New Prompt
                              </Button>
                            </NewPromptModal>
                          </SelectContent>
                        </Select>

                        <ViewStrategyModal
                          prompt={prompts.find(
                            (prompt) => prompt.id === field.state.value,
                          )}
                        >
                          <Button
                            type="button"
                            variant="outline"
                            className="hover:bg-gray-50"
                          >
                            <Eye />
                            View Strategy
                          </Button>
                        </ViewStrategyModal>
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
