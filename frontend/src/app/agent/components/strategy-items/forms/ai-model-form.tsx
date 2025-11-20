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
          {(field) => {
            return (
              <Field>
                <FieldLabel className="font-medium text-base text-gray-950">
                  Model Platform
                </FieldLabel>
                <Select
                  value={field.state.value}
                  onValueChange={(value) => {
                    field.handleChange(value);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
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
                  </SelectContent>
                </Select>
                <FieldError errors={field.state.meta.errors} />
              </Field>
            );
          }}
        </form.AppField>

        <form.AppField name="model_id">
          {(field) => {
            const currentProvider = form.state.values
              .provider as keyof typeof MODEL_PROVIDER_MAP;
            const availableModels = MODEL_PROVIDER_MAP[currentProvider] || [];

            return (
              <Field key={currentProvider}>
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
                <FieldError errors={field.state.meta.errors} />
              </Field>
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
