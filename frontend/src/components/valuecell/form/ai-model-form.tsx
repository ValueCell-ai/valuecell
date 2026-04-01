import { useStore } from "@tanstack/react-form";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  useGetModelProviderDetail,
  useGetSortedModelProviders,
} from "@/api/setting";
import { FieldGroup } from "@/components/ui/field";
import { SelectItem } from "@/components/ui/select";
import PngIcon from "@/components/valuecell/icon/png-icon";
import { MODEL_PROVIDER_ICONS } from "@/constants/icons";
import { withForm } from "@/hooks/use-form";

export const AIModelForm = withForm({
  defaultValues: {
    model_id: "",
    provider: "",
    api_key: "",
  },

  render({ form }) {
    const { t } = useTranslation();
    const {
      providers: sortedProviders,
      defaultProvider,
      isLoading: isLoadingProviders,
    } = useGetSortedModelProviders();

    const provider = useStore(form.store, (state) => state.values.provider);
    const {
      isLoading: isLoadingModelProviderDetail,
      data: modelProviderDetail,
      refetch: fetchModelProviderDetail,
    } = useGetModelProviderDetail(provider);

    const isAnthropic = provider === "anthropic";

    // Set the default provider once loaded and provider is not yet selected
    useEffect(() => {
      if (isLoadingProviders || !defaultProvider) return;
      // Only set if provider field is empty (not yet selected by user)
      if (!provider) {
        form.setFieldValue("provider", defaultProvider);
      }
    }, [isLoadingProviders, defaultProvider, provider]);

    if (isLoadingProviders || isLoadingModelProviderDetail) {
      return <div>Loading...</div>;
    }

    return (
      <FieldGroup className="gap-6">
        <form.AppField
          listeners={{
            onMount: async () => {
              const { data } = await fetchModelProviderDetail();
              form.setFieldValue("api_key", data?.api_key ?? "");
            },
            onChange: async () => {
              const { data } = await fetchModelProviderDetail();

              form.setFieldValue("model_id", data?.default_model_id ?? "");
              form.setFieldValue("api_key", data?.api_key ?? "");
            },
          }}
          name="provider"
        >
          {(field) => (
            <field.SelectField label={t("strategy.form.aiModels.platform")}>
              {sortedProviders.map(({ provider }) => (
                <SelectItem key={provider} value={provider}>
                  <div className="flex items-center gap-2">
                    <PngIcon
                      src={
                        MODEL_PROVIDER_ICONS[
                          provider as keyof typeof MODEL_PROVIDER_ICONS
                        ]
                      }
                      className="size-4"
                    />
                    {t(`strategy.providers.${provider}`) || provider}
                  </div>
                </SelectItem>
              ))}
            </field.SelectField>
          )}
        </form.AppField>

        <form.AppField name="model_id">
          {(field) => {
            const models = modelProviderDetail?.models || [];

            return (
              <field.SelectField label={t("strategy.form.aiModels.model")}>
                {models.map((m) => (
                  <SelectItem key={m.model_id} value={m.model_id}>
                    {m.model_name}
                  </SelectItem>
                ))}
              </field.SelectField>
            );
          }}
        </form.AppField>

        {/* Hide API key field for Anthropic — uses OAuth token from environment */}
        {!isAnthropic && (
          <form.AppField name="api_key">
            {(field) => (
              <field.PasswordField
                label={t("strategy.form.aiModels.apiKey.label")}
                placeholder={t("strategy.form.aiModels.apiKey.placeholder")}
              />
            )}
          </form.AppField>
        )}

        {/* Anthropic: show info about OAuth token */}
        {isAnthropic && (
          <div className="rounded-lg border border-border bg-muted/40 px-4 py-3">
            <p className="text-sm font-medium text-foreground">OAuth Token</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Anthropic uses an OAuth token (
              <code className="text-xs">ANTHROPIC_AUTH_TOKEN</code>) configured
              in the server environment. No API key needed here.
            </p>
          </div>
        )}
      </FieldGroup>
    );
  },
});
