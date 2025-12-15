import { MultiSelect } from "@valuecell/multi-select";
import { Eye, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  useCreateStrategyPrompt,
  useDeleteStrategyPrompt,
} from "@/api/strategy";
import NewPromptModal from "@/app/agent/components/strategy-items/modals/new-prompt-modal";
import ViewStrategyModal from "@/app/agent/components/strategy-items/modals/view-strategy-modal";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
    const { t } = useTranslation();
    const { mutateAsync: createStrategyPrompt } = useCreateStrategyPrompt();
    const { mutate: deleteStrategyPrompt } = useDeleteStrategyPrompt();
    const [deletePromptId, setDeletePromptId] = useState<string | null>(null);
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

    const handleDeletePrompt = (promptId: string) => {
      setDeletePromptId(promptId);
      setIsDeleteDialogOpen(true);
    };

    const confirmDeletePrompt = () => {
      if (deletePromptId) {
        deleteStrategyPrompt(deletePromptId, {
          onSuccess: () => {
            // If the deleted prompt was currently selected, clear the selection
            if (form.state.values.template_id === deletePromptId) {
              form.setFieldValue("template_id", "");
            }
            setIsDeleteDialogOpen(false);
            setDeletePromptId(null);
          },
          onError: () => {
            setIsDeleteDialogOpen(false);
            setDeletePromptId(null);
          },
        });
      }
    };

    const cancelDeletePrompt = () => {
      setIsDeleteDialogOpen(false);
      setDeletePromptId(null);
    };

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
            <field.SelectField label={t("strategy.form.strategyType.label")}>
              <SelectItem value="PromptBasedStrategy">
                {t("strategy.form.strategyType.promptBased")}
              </SelectItem>
              <SelectItem value="GridStrategy">
                {t("strategy.form.strategyType.grid")}
              </SelectItem>
            </field.SelectField>
          )}
        </form.AppField>

        <form.AppField name="strategy_name">
          {(field) => (
            <field.TextField
              label={t("strategy.form.strategyName.label")}
              placeholder={t("strategy.form.strategyName.placeholder")}
            />
          )}
        </form.AppField>

        <FieldGroup className="flex flex-row gap-4">
          {tradingMode === "virtual" && (
            <form.AppField name="initial_capital">
              {(field) => (
                <field.NumberField
                  className="flex-1"
                  label={t("strategy.form.initialCapital.label")}
                  placeholder={t("strategy.form.initialCapital.placeholder")}
                />
              )}
            </form.AppField>
          )}

          <form.AppField name="max_leverage">
            {(field) => (
              <field.NumberField
                className="flex-1"
                label={t("strategy.form.maxLeverage.label")}
                placeholder={t("strategy.form.maxLeverage.placeholder")}
              />
            )}
          </form.AppField>
        </FieldGroup>

        <form.AppField name="decide_interval">
          {(field) => (
            <field.NumberField
              label={t("strategy.form.decideInterval.label")}
              placeholder={t("strategy.form.decideInterval.placeholder")}
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
                      {t("strategy.form.tradingSymbols.label")}
                    </FieldLabel>
                    <MultiSelect
                      maxSelected={
                        strategyType === "GridStrategy" ? 1 : undefined
                      }
                      options={TRADING_SYMBOLS}
                      value={field.state.value}
                      onValueChange={(value) => field.handleChange(value)}
                      placeholder={t(
                        "strategy.form.tradingSymbols.placeholder",
                      )}
                      searchPlaceholder={t(
                        "strategy.form.tradingSymbols.searchPlaceholder",
                      )}
                      emptyText={t("strategy.form.tradingSymbols.emptyText")}
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
                        {t("strategy.form.promptTemplate.label")}
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
                                <SelectItem
                                  key={prompt.id}
                                  value={prompt.id}
                                  className="relative hover:[&_button]:opacity-100 hover:[&_button]:transition-opacity"
                                >
                                  <span>{prompt.name}</span>
                                  {field.state.value !== prompt.id && (
                                    <button
                                      type="button"
                                      className="absolute right-2 z-50 flex size-3.5 items-center justify-center rounded-sm p-0 opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive hover:opacity-100"
                                      onPointerUp={(e) => {
                                        e.stopPropagation();
                                        e.preventDefault();
                                        handleDeletePrompt(prompt.id);
                                      }}
                                    >
                                      <Trash2 className="h-3 w-3" />
                                    </button>
                                  )}
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
                                {t("strategy.form.promptTemplate.new")}
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
                            {t("strategy.form.promptTemplate.view")}
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

        {/* Delete Confirmation Dialog */}
        <AlertDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {t("strategy.prompt.delete.title")}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {t("strategy.prompt.delete.description")}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={cancelDeletePrompt}>
                {t("strategy.action.cancel")}
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={confirmDeletePrompt}
                className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
              >
                {t("strategy.action.confirmDelete")}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </FieldGroup>
    );
  },
});
