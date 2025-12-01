import { useStore } from "@tanstack/react-form";
import { useQueries } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
import { useGetModelProviderDetail, useGetModelProviders } from "@/api/setting";
import { FieldGroup } from "@/components/ui/field";
import { SelectItem } from "@/components/ui/select";
import PngIcon from "@/components/valuecell/icon/png-icon";
import { API_QUERY_KEYS } from "@/constants/api";
import { MODEL_PROVIDER_ICONS } from "@/constants/icons";
import { withForm } from "@/hooks/use-form";
import type { ApiResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import type { ProviderDetail } from "@/types/setting";

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

    // Fetch details for all providers to check API key availability
    const providerDetailsQueries = useQueries({
      queries: modelProviders.map((p) => ({
        queryKey: API_QUERY_KEYS.SETTING.modelProviderDetail([p.provider]),
        queryFn: () =>
          apiClient.get<ApiResponse<ProviderDetail>>(
            `/models/providers/${p.provider}`,
          ),
        select: (data: ApiResponse<ProviderDetail>) => ({
          provider: p.provider,
          hasApiKey: !!data.data?.api_key,
        }),
        staleTime: 5 * 60 * 1000, // Cache for 5 minutes
      })),
    });

    // Check if all provider details are loaded
    const isLoadingProviderDetails =
      providerDetailsQueries.length > 0 &&
      providerDetailsQueries.some((q) => q.isLoading);

    // Sort providers: those with API keys first
    const sortedProviders = useMemo(() => {
      const apiKeyMap = new Map<string, boolean>();
      for (const query of providerDetailsQueries) {
        if (query.data) {
          apiKeyMap.set(query.data.provider, query.data.hasApiKey);
        }
      }

      return [...modelProviders].sort((a, b) => {
        const aHasKey = apiKeyMap.get(a.provider) ?? false;
        const bHasKey = apiKeyMap.get(b.provider) ?? false;
        if (aHasKey && !bHasKey) return -1;
        if (!aHasKey && bHasKey) return 1;
        return 0;
      });
    }, [modelProviders, providerDetailsQueries]);

    // Get the first provider with API key, or the first provider if none have keys
    const defaultProvider = useMemo(() => {
      if (sortedProviders.length === 0) return "";
      return sortedProviders[0].provider;
    }, [sortedProviders]);

    // Set the default provider once all details are loaded and provider is not yet selected
    useEffect(() => {
      if (isLoadingProviderDetails) return;
      if (!defaultProvider) return;
      // Only set if provider field is empty (not yet selected by user)
      if (!provider) {
        form.setFieldValue("provider", defaultProvider);
      }
    }, [isLoadingProviderDetails, defaultProvider, provider]);

    useEffect(() => {
      if (!modelProviderDetail) return;

      form.setFieldValue(
        "model_id",
        modelProviderDetail.default_model_id ?? "",
      );
      form.setFieldValue("api_key", modelProviderDetail.api_key ?? "");
    }, [modelProviderDetail]);

    // Show loading while fetching providers or their details
    if (isLoadingModelProviders || isLoadingProviderDetails) {
      return <div>Loading...</div>;
    }

    return (
      <FieldGroup className="gap-6">
        <form.AppField name="provider" defaultValue={defaultProvider}>
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
