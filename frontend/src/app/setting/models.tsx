import { useState } from "react";

import {
  useAddProviderModel,
  useDeleteProviderModel,
  useGetModelProviderDetail,
  useGetModelProviders,
  useSetDefaultProvider,
  useUpdateProviderConfig,
} from "@/api/setting";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export default function ModelsSettingPage() {
  const { data: providers = [], isLoading: providersLoading } =
    useGetModelProviders();
  const [selectedProvider, setSelectedProvider] = useState<string | undefined>(
    undefined,
  );

  const currentProvider =
    selectedProvider || (providers.length > 0 ? providers[0]?.provider : "");

  const { data: providerDetail, isLoading: detailLoading } =
    useGetModelProviderDetail(currentProvider);

  const { mutate: updateConfig, isPending: updatingConfig } =
    useUpdateProviderConfig();
  const { mutate: addModel, isPending: addingModel } = useAddProviderModel();
  const { mutate: deleteModel, isPending: deletingModel } =
    useDeleteProviderModel();
  const { mutate: setDefault, isPending: settingDefault } =
    useSetDefaultProvider();

  const [apiKeyInput, setApiKeyInput] = useState("");
  const [baseUrlInput, setBaseUrlInput] = useState("");
  const [newModelId, setNewModelId] = useState("");
  const [newModelName, setNewModelName] = useState("");

  const handleSaveConfig = () => {
    if (!currentProvider) return;

    updateConfig({
      provider: currentProvider,
      api_key: apiKeyInput || providerDetail?.api_key,
      base_url: baseUrlInput || providerDetail?.base_url,
    });
  };

  const handleAddModel = () => {
    if (!currentProvider || !newModelId || !newModelName) return;

    addModel({
      provider: currentProvider,
      model_id: newModelId,
      model_name: newModelName,
    });
    setNewModelId("");
    setNewModelName("");
  };

  const handleDeleteModel = (modelId: string) => {
    if (!currentProvider) return;
    deleteModel({ provider: currentProvider, model_id: modelId });
  };

  const handleSetDefaultProvider = () => {
    if (!currentProvider) return;
    setDefault({ provider: currentProvider });
  };

  const isBusy =
    updatingConfig || addingModel || deletingModel || settingDefault;

  return (
    <div className="flex flex-col gap-5 px-16 py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-bold text-gray-950 text-xl">Model Providers</h1>
        <p className="text-base text-gray-400 leading-[22px]">
          Manage your LLM providers, API keys and available models.
        </p>
      </div>

      <div className="flex gap-8">
        {/* Provider list */}
        <div className="w-64 space-y-3">
          <div className="font-medium text-gray-500 text-xs uppercase">
            Providers
          </div>

          {providersLoading ? (
            <div className="text-gray-400 text-sm">Loading providers...</div>
          ) : providers.length === 0 ? (
            <div className="text-gray-400 text-sm">No providers found.</div>
          ) : (
            <div className="flex flex-col gap-2">
              {providers.map((p) => {
                const isActive = currentProvider === p.provider;
                return (
                  <button
                    key={p.provider}
                    type="button"
                    className={cn(
                      "flex items-center justify-between rounded-lg border px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "border-gray-900 bg-gray-900 text-white"
                        : "border-gray-200 bg-white text-gray-800 hover:bg-gray-50",
                    )}
                    onClick={() => setSelectedProvider(p.provider)}
                  >
                    <span className="truncate">{p.provider}</span>
                    {providerDetail?.is_default && isActive && (
                      <span className="rounded bg-emerald-500 px-1.5 py-0.5 font-medium text-white text-xs">
                        Default
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Provider detail */}
        <div className="flex-1 space-y-6">
          {detailLoading && (
            <div className="text-gray-400 text-sm">
              Loading provider details...
            </div>
          )}

          {providerDetail && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold text-gray-900 text-sm">
                    {currentProvider}
                  </div>
                  <div className="text-gray-500 text-xs">
                    Default model: {providerDetail.default_model_id}
                  </div>
                </div>

                <Button
                  size="sm"
                  variant={providerDetail.is_default ? "outline" : "default"}
                  disabled={providerDetail.is_default || isBusy}
                  onClick={handleSetDefaultProvider}
                >
                  {providerDetail.is_default
                    ? "Default provider"
                    : "Set default"}
                </Button>
              </div>

              <div className="space-y-4 rounded-xl border border-gray-100 bg-gray-50 p-4">
                <div className="space-y-2">
                  <label
                    htmlFor="api-key"
                    className="font-medium text-gray-700 text-xs"
                  >
                    API Key
                  </label>
                  <Input
                    type="password"
                    placeholder={
                      providerDetail.api_key
                        ? "●●●●●●●●●●●●●●●●"
                        : "Enter API key"
                    }
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor="base-url"
                    className="font-medium text-gray-700 text-xs"
                  >
                    Base URL
                  </label>
                  <Input
                    placeholder={
                      providerDetail.base_url || "https://api.example.com/v1"
                    }
                    value={baseUrlInput}
                    onChange={(e) => setBaseUrlInput(e.target.value)}
                  />
                </div>

                <Button
                  size="sm"
                  className="mt-2"
                  disabled={isBusy}
                  onClick={handleSaveConfig}
                >
                  Save configuration
                </Button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-gray-900 text-sm">
                    Models
                  </div>

                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="Model ID"
                      value={newModelId}
                      onChange={(e) => setNewModelId(e.target.value)}
                      className="h-8 w-48"
                    />
                    <Input
                      placeholder="Model name"
                      value={newModelName}
                      onChange={(e) => setNewModelName(e.target.value)}
                      className="h-8 w-48"
                    />
                    <Button
                      size="sm"
                      disabled={isBusy || !newModelId || !newModelName}
                      onClick={handleAddModel}
                    >
                      Add model
                    </Button>
                  </div>
                </div>

                {providerDetail.models.length === 0 ? (
                  <div className="rounded-lg border border-gray-200 border-dashed p-4 text-gray-400 text-sm">
                    No models configured for this provider.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {providerDetail.models.map((m) => (
                      <div
                        key={m.model_id}
                        className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 text-sm"
                      >
                        <div className="flex flex-col">
                          <span className="font-medium text-gray-900">
                            {m.model_name}
                          </span>
                          <span className="text-gray-500 text-xs">
                            {m.model_id}
                          </span>
                        </div>

                        <div className="flex items-center gap-3">
                          <Select
                            defaultValue={providerDetail.default_model_id}
                          >
                            <SelectTrigger className="h-8 w-40 text-xs">
                              <SelectValue placeholder="Default model" />
                            </SelectTrigger>
                            <SelectContent>
                              {providerDetail.models.map((option) => (
                                <SelectItem
                                  key={option.model_id}
                                  value={option.model_id}
                                >
                                  {option.model_name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>

                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-500 text-xs hover:text-red-600"
                            disabled={isBusy}
                            onClick={() => handleDeleteModel(m.model_id)}
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
