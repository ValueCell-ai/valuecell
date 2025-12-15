import { DialogDescription } from "@radix-ui/react-dialog";
import { useForm } from "@tanstack/react-form";
import { Eye, EyeOff, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import {
  useAddProviderModel,
  useCheckModelAvailability,
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
import LinkButton from "@/components/valuecell/button/link-button";

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
  const { t } = useTranslation();

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
  const {
    data: checkResult,
    mutateAsync: checkAvailability,
    isPending: checkingAvailability,
    reset: resetCheckResult,
  } = useCheckModelAvailability();

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
    if (provider) {
      setShowApiKey(false);
      resetCheckResult();
    }
  }, [provider, resetCheckResult]);

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
    settingDefaultProvider ||
    checkingAvailability;

  if (detailLoading) {
    return (
      <div className="text-gray-400 text-sm">
        {t("settings.models.loading")}
      </div>
    );
  }

  if (!providerDetail) {
    return null;
  }

  return (
    <div className="scroll-container flex flex-1 flex-col px-8">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-semibold text-gray-950 text-lg">
          {t(`strategy.providers.${provider}`) || provider}
        </p>
        <div className="flex items-center gap-2">
          <p className="font-semibold text-base text-gray-700">
            {t("settings.models.defaultProvider")}
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
                    {t("settings.models.apiKey")}
                  </FieldLabel>
                  <div className="flex items-center gap-4">
                    <InputGroup>
                      <InputGroupInput
                        type={showApiKey ? "text" : "password"}
                        id="api_key"
                        placeholder={t("settings.models.enterApiKey")}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={() => configForm.handleSubmit()}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            e.currentTarget.blur();
                          }
                        }}
                      />
                      <InputGroupAddon align="inline-end">
                        <InputGroupButton
                          type="button"
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => setShowApiKey(!showApiKey)}
                          aria-label={
                            showApiKey
                              ? t("settings.models.hidePassword")
                              : t("settings.models.showPassword")
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

                    <Button
                      type="button"
                      variant={"outline"}
                      disabled={isBusy}
                      onClick={async () => {
                        await checkAvailability({
                          provider,
                          model_id: providerDetail.default_model_id,
                        });
                      }}
                    >
                      {checkingAvailability
                        ? t("settings.models.waitingForCheck")
                        : t("settings.models.checkAvailability")}
                    </Button>
                  </div>
                  {checkResult?.data && (
                    <div className="text-sm">
                      {checkResult.data.ok ? (
                        <span className="text-green-600">
                          {t("settings.models.available")}
                          {checkResult.data.status
                            ? ` (${checkResult.data.status})`
                            : ""}
                        </span>
                      ) : (
                        <span className="text-red-600">
                          {t("settings.models.unavailable")}
                          {checkResult.data.status
                            ? ` (${checkResult.data.status})`
                            : ""}
                          {checkResult.data.error
                            ? `: ${checkResult.data.error}`
                            : ""}
                        </span>
                      )}
                    </div>
                  )}
                  <LinkButton
                    className="w-fit! hover:text-gray-700"
                    url={providerDetail.api_key_url}
                  >
                    {t("settings.models.getApiKey")}
                  </LinkButton>
                  <FieldError errors={field.state.meta.errors} />
                </Field>
              )}
            </configForm.Field>

            {/* API Host section */}
            <configForm.Field name="base_url">
              {(field) => (
                <Field className="text-gray-950">
                  <FieldLabel className="font-medium text-base">
                    {t("settings.models.apiHost")}
                  </FieldLabel>
                  <Input
                    placeholder={providerDetail.base_url}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={() => configForm.handleSubmit()}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        e.currentTarget.blur();
                      }
                    }}
                  />
                  <FieldError errors={field.state.meta.errors} />
                </Field>
              )}
            </configForm.Field>
          </FieldGroup>

          {/* Models section */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="font-medium text-base text-gray-950">
                {t("settings.models.models")}
              </div>
              <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
                <DialogTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 border-gray-200 px-2.5 font-semibold text-gray-700 text-sm"
                    disabled={isBusy}
                  >
                    <Plus className="size-4" />
                    {t("settings.models.add")}
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
                      <DialogTitle>{t("settings.models.addModel")}</DialogTitle>
                      <DialogDescription />
                    </DialogHeader>
                    <div className="flex flex-col gap-4 py-4">
                      <FieldGroup className="gap-4">
                        <addModelForm.Field name="model_id">
                          {(field) => (
                            <Field>
                              <FieldLabel className="font-medium text-sm">
                                {t("settings.models.modelId")}
                              </FieldLabel>
                              <Input
                                placeholder={t("settings.models.enterModelId")}
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
                                {t("settings.models.modelName")}
                              </FieldLabel>
                              <Input
                                placeholder={t(
                                  "settings.models.enterModelName",
                                )}
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
                        {t("settings.models.cancel")}
                      </Button>
                      <Button
                        className="flex-1"
                        type="submit"
                        disabled={isBusy || !addModelForm.state.canSubmit}
                      >
                        {t("settings.models.confirm")}
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </div>

            {providerDetail.models.length === 0 ? (
              <div className="rounded-lg border border-gray-200 border-dashed p-4 text-gray-400 text-sm">
                {t("settings.models.noModels")}
              </div>
            ) : (
              <div className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3">
                {[...providerDetail.models]
                  .sort((a, b) => a.model_name.localeCompare(b.model_name))
                  .map((m) => (
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
                          checked={
                            m.model_id === providerDetail.default_model_id
                          }
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
    </div>
  );
}
