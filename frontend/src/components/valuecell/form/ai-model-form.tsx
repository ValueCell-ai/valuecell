import { useStore } from "@tanstack/react-form";
import { useEffect } from "react";
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
            <field.SelectField label="Model Platform">
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
                    {provider}
                  </div>
                </SelectItem>
              ))}
            </field.SelectField>
          )}
        </form.AppField>

        <form.AppField name="model_id">
          {(field) => (
            <field.SelectField label="Select Model">
              {modelProviderDetail?.models &&
              modelProviderDetail?.models.length > 0 ? (
                modelProviderDetail?.models.map(
                  (model) =>
                    model.model_id && (
                      <SelectItem key={model.model_id} value={model.model_id}>
                        {model.model_name}
                      </SelectItem>
                    ),
                )
              ) : (
                <SelectItem value="__no_models_available__" disabled>
                  No models available
                </SelectItem>
              )}
            </field.SelectField>
          )}
        </form.AppField>

        <form.AppField name="api_key">
          {(field) => (
            <field.PasswordField label="API key" placeholder="Enter API Key" />
          )}
        </form.AppField>
      </FieldGroup>
    );
  },
});
