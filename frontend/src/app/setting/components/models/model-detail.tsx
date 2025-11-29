import { DialogDescription } from "@radix-ui/react-dialog";
import { useForm } from "@tanstack/react-form";
import { openUrl } from "@tauri-apps/plugin-opener";
import { Eye, EyeOff, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { z } from "zod";
import {
  useAddProviderModel,
  useDeleteProviderModel,
  useGetModelProviderDetail,
  useSetDefaultProvider,
  useSetDefaultProviderModel,
  useUpdateProviderConfig,
} from "@/api/setting";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Switch } from "@/components/ui/switch";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { useTauriInfo } from "@/hooks/use-tauri-info";

const configSchema = z.object({
  api_key: z.string(),
  base_url: z.string(),
});

const addModelSchema = z.object({
  model_id: z.string().min(1, "Model ID is required"),
  model_name: z.string().min(1, "Model name is required"),
});

type ModelDetailProps = {
  provider: string;
};

export function ModelDetail({ provider }: ModelDetailProps) {
  const { isTauriApp } = useTauriInfo();

  const { data: providerDetail, isLoading: detailLoading } =
    useGetModelProviderDetail(provider);
  const { mutate: updateConfig, isPending: updatingConfig } =
    useUpdateProviderConfig();
  const { mutate: addModel, isPending: addingModel } = useAddProviderModel();
  const { mutate: deleteModel, isPending: deletingModel } =
    useDeleteProviderModel();
  const { mutate: setDefaultModel, isPending: settingDefaultModel } =
    useSetDefaultProviderModel();
  const { mutate: setDefaultProvider, isPending: settingDefaultProvider } =
    useSetDefaultProvider();

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  const configForm = useForm({
    defaultValues: {
      api_key: "",
      base_url: "",
    },
    validators: {
      onSubmit: configSchema,
    },
    onSubmit: async ({ value }) => {
      if (!provider) return;
      updateConfig({
        provider,
        api_key: value.api_key,
        base_url: value.base_url,
      });
    },
  });

  useEffect(() => {
    if (providerDetail) {
      configForm.setFieldValue("api_key", providerDetail.api_key || "");
      configForm.setFieldValue("base_url", providerDetail.base_url || "");
    }
  }, [providerDetail, configForm.setFieldValue]);

  useEffect(() => {
    if (provider) setShowApiKey(false);
  }, [provider]);

  const addModelForm = useForm({
    defaultValues: {
      model_id: "",
      model_name: "",
    },
    validators: {
      onSubmit: addModelSchema,
    },
    onSubmit: async ({ value }) => {
      if (!provider) return;
      addModel({
        provider,
        model_id: value.model_id,
        model_name: value.model_name,
      });
      addModelForm.reset();
      setIsAddDialogOpen(false);
    },
  });

  const handleSetDefaultModel = (modelId: string) => {
    if (!provider) return;
    setDefaultModel({ provider, model_id: modelId });
  };

  const handleDeleteModel = (modelId: string) => {
    if (!provider) return;
    deleteModel({ provider, model_id: modelId });
  };

  const isBusy =
    updatingConfig ||
    addingModel ||
    deletingModel ||
    settingDefaultModel ||
    settingDefaultProvider;

  if (detailLoading) {
    return (
      <div className="text-gray-400 text-sm">Loading provider details...</div>
    );
  }

  if (!providerDetail) {
    return null;
  }

  return (
    <ScrollContainer className="flex flex-1 flex-col px-8">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-semibold text-gray-950 text-lg">{provider}</p>
        <div className="flex items-center gap-2">
          <p className="font-semibold text-base text-gray-700">
            Default Provider
          </p>
          <Switch
            checked={providerDetail.is_default}
            disabled={isBusy}
            onCheckedChange={() => setDefaultProvider({ provider })}
          />
        </div>
      </div>

      <form>
        <div className="flex flex-col gap-6">
          <FieldGroup>
            <configForm.Field name="api_key">
              {(field) => (
                <Field className="text-gray-950">
                  <FieldLabel
                    htmlFor="api_key"
                    className="font-medium text-base"
                  >
                    API key
                  </FieldLabel>
                  <InputGroup>
                    <InputGroupInput
                      type={showApiKey ? "text" : "password"}
                      id="api_key"
                      placeholder={"Enter API key"}
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={() => configForm.handleSubmit()}
                    />
                    <InputGroupAddon align="inline-end">
                      <InputGroupButton
                        type="button"
                        variant="ghost"
                        size="icon-xs"
                        onClick={() => setShowApiKey(!showApiKey)}
                        aria-label={
                          showApiKey ? "Hide password" : "Show password"
                        }
                      >
                        {showApiKey ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </InputGroupButton>
                    </InputGroupAddon>
                  </InputGroup>
                  <button
                    type="button"
                    onClick={() =>
                      isTauriApp
                        ? openUrl(providerDetail.api_key_url)
                        : window.open(providerDetail.api_key_url, "_blank")
                    }
                    className="w-fit! cursor-pointer text-sm underline underline-offset-4 hover:text-gray-700"
                  >
                    Click here to get the API key
                  </button>
                  <FieldError errors={field.state.meta.errors} />
                </Field>
              )}
            </configForm.Field>

            {/* API Host section */}
            <configForm.Field name="base_url">
              {(field) => (
                <Field className="text-gray-950">
                  <FieldLabel className="font-medium text-base">
                    API Host
                  </FieldLabel>
                  <Input
                    placeholder={providerDetail.base_url}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={() => configForm.handleSubmit()}
                  />
                  <FieldError errors={field.state.meta.errors} />
                </Field>
              )}
            </configForm.Field>
          </FieldGroup>

          {/* Models section */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="font-medium text-base text-gray-950">Models</div>
              <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
                <DialogTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 border-gray-200 px-2.5 font-semibold text-gray-700 text-sm"
                    disabled={isBusy}
                  >
                    <Plus className="size-4" />
                    Add
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      addModelForm.handleSubmit();
                    }}
                  >
                    <DialogHeader>
                      <DialogTitle>Add Model</DialogTitle>
                      <DialogDescription />
                    </DialogHeader>
                    <div className="flex flex-col gap-4 py-4">
                      <FieldGroup className="gap-4">
                        <addModelForm.Field name="model_id">
                          {(field) => (
                            <Field>
                              <FieldLabel className="font-medium text-sm">
                                Model ID
                              </FieldLabel>
                              <Input
                                placeholder="Enter model ID"
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(e.target.value)
                                }
                                onBlur={field.handleBlur}
                              />
                              <FieldError errors={field.state.meta.errors} />
                            </Field>
                          )}
                        </addModelForm.Field>

                        <addModelForm.Field name="model_name">
                          {(field) => (
                            <Field>
                              <FieldLabel className="font-medium text-sm">
                                Model Name
                              </FieldLabel>
                              <Input
                                placeholder="Enter model name"
                                value={field.state.value}
                                onChange={(e) =>
                                  field.handleChange(e.target.value)
                                }
                                onBlur={field.handleBlur}
                              />
                              <FieldError errors={field.state.meta.errors} />
                            </Field>
                          )}
                        </addModelForm.Field>
                      </FieldGroup>
                    </div>
                    <DialogFooter>
                      <Button
                        className="flex-1"
                        type="button"
                        variant="outline"
                        onClick={() => {
                          addModelForm.reset();
                          setIsAddDialogOpen(false);
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        className="flex-1"
                        type="submit"
                        disabled={isBusy || !addModelForm.state.canSubmit}
                      >
                        Confirm
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </div>

            {providerDetail.models.length === 0 ? (
              <div className="rounded-lg border border-gray-200 border-dashed p-4 text-gray-400 text-sm">
                No models configured for this provider.
              </div>
            ) : (
              <div className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3">
                {providerDetail.models.map((m) => (
                  <div
                    key={m.model_id}
                    className="flex items-center justify-between"
                  >
                    <span className="font-normal text-gray-950 text-sm">
                      {m.model_name}
                    </span>

                    <div className="flex items-center gap-3">
                      <Switch
                        className="cursor-pointer"
                        checked={m.model_id === providerDetail.default_model_id}
                        disabled={isBusy}
                        onCheckedChange={() =>
                          handleSetDefaultModel(m.model_id)
                        }
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        disabled={isBusy}
                        onClick={() => handleDeleteModel(m.model_id)}
                      >
                        <Trash2 className="size-5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </form>
    </ScrollContainer>
  );
}
