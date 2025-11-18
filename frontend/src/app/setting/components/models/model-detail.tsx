import { useForm } from "@tanstack/react-form";
import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink } from "react-router";

import { z } from "zod";
import {
  useAddProviderModel,
  useDeleteProviderModel,
  useGetModelProviderDetail,
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
import { Switch } from "@/components/ui/switch";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";

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
  const { data: providerDetail, isLoading: detailLoading } =
    useGetModelProviderDetail(provider);

  const { mutate: updateConfig, isPending: updatingConfig } =
    useUpdateProviderConfig();
  const { mutate: addModel, isPending: addingModel } = useAddProviderModel();
  const { mutate: deleteModel, isPending: deletingModel } =
    useDeleteProviderModel();
  const { mutate: setDefaultModel, isPending: settingDefaultModel } =
    useSetDefaultProviderModel();

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

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
        api_key: value.api_key || providerDetail?.api_key,
        base_url: value.base_url || providerDetail?.base_url,
      });
    },
  });

  useEffect(() => {
    if (providerDetail) {
      configForm.setFieldValue("api_key", providerDetail.api_key || "");
      configForm.setFieldValue("base_url", providerDetail.base_url || "");
    }
  }, [providerDetail, configForm]);

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
    updatingConfig || addingModel || deletingModel || settingDefaultModel;

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
      <form>
        <div className="flex flex-col gap-6">
          <FieldGroup>
            <configForm.Field name="api_key">
              {(field) => (
                <Field className="text-gray-950">
                  <FieldLabel className="font-medium text-base">
                    API key
                  </FieldLabel>
                  <Input
                    type="password"
                    placeholder={"Enter API key"}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={() => configForm.handleSubmit()}
                  />
                  <NavLink
                    to={providerDetail.api_key_url}
                    target="_blank"
                    className="text-sm underline underline-offset-4"
                  >
                    Click here to get the API key
                  </NavLink>
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
          <div className="flex flex-col gap-4">
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
                    className="flex items-center justify-between py-2"
                  >
                    <span className="font-normal text-base text-gray-950">
                      {m.model_name}
                    </span>

                    <div className="flex items-center gap-3">
                      <Switch
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
