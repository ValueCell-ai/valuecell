import { useStore } from "@tanstack/react-form";
import { useEffect } from "react";
import { useGetModelProviderDetail, useGetModelProviders } from "@/api/setting";
import { FieldGroup } from "@/components/ui/field";
import { SelectItem } from "@/components/ui/select";
import PngIcon from "@/components/valuecell/png-icon";
import { MODEL_PROVIDER_ICONS } from "@/constants/icons";
import { withForm } from "@/hooks/use-form";

export const AIModelForm = withForm({
  defaultValues: {
    model_id: "",
    provider: "",
    api_key: "",
  },

  render({ form }) {
    const { data: modelProviders = [], isLoading: isLoadingModelProviders } =
      useGetModelProviders();
    const provider = useStore(form.store, (state) => state.values.provider);
    const { data: modelProviderDetail } = useGetModelProviderDetail(provider);

    useEffect(() => {
      if (!modelProviderDetail) return;

      form.setFieldValue(
        "model_id",
        modelProviderDetail.default_model_id ?? "",
      );
      form.setFieldValue("api_key", modelProviderDetail.api_key ?? "");
    }, [modelProviderDetail]);

    if (isLoadingModelProviders) return <div>Loading...</div>;

    return (
      <FieldGroup className="gap-6">
        <form.AppField
          name="provider"
          defaultValue={
            modelProviders.length > 0 ? modelProviders[0].provider : ""
          }
        >
          {(field) => (
            <field.SelectField label="Model Platform">
              {modelProviders.map(({ provider }) => (
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
