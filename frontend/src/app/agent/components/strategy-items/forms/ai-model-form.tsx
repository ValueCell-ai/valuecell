import { FieldGroup } from "@/components/ui/field";
import { SelectItem } from "@/components/ui/select";
import PngIcon from "@/components/valuecell/png-icon";
import { MODEL_PROVIDER_MAP, MODEL_PROVIDERS } from "@/constants/agent";
import { MODEL_PROVIDER_ICONS } from "@/constants/icons";
import { withForm } from "@/hooks/use-form";
import type { LlmConfig } from "@/types/strategy";

export const AIModelForm = withForm({
  defaultValues: {
    model_id: "",
    provider: "",
    api_key: "",
  },
  props: {
    llms: [] as LlmConfig[],
  },
  render({ form, llms }) {
    return (
      <FieldGroup className="gap-6">
        <form.AppField
          listeners={{
            onChange: ({ value }) => {
              form.setFieldValue(
                "model_id",
                MODEL_PROVIDER_MAP[value as keyof typeof MODEL_PROVIDER_MAP][0],
              );
              const api_key = llms.find(
                (config) => config.provider === value,
              )?.api_key;
              if (api_key) form.setFieldValue("api_key", api_key);
            },
          }}
          name="provider"
        >
          {(field) => (
            <field.SelectField label="Model Platform">
              {MODEL_PROVIDERS.map((provider) => (
                <SelectItem key={provider} value={provider}>
                  <div className="flex items-center gap-2">
                    <PngIcon
                      src={MODEL_PROVIDER_ICONS[provider]}
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
          {(field) => {
            const currentProvider = form.state.values
              .provider as keyof typeof MODEL_PROVIDER_MAP;
            const availableModels = MODEL_PROVIDER_MAP[currentProvider] || [];

            return (
              <field.SelectField label="Select Model">
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
              </field.SelectField>
            );
          }}
        </form.AppField>

        <form.AppField name="api_key">
          {(field) => (
            <field.TextField label="API key" placeholder="Enter API Key" />
          )}
        </form.AppField>
      </FieldGroup>
    );
  },
});
