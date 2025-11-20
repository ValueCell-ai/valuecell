import { createFormHook, createFormHookContexts } from "@tanstack/react-form";
import { TextField } from "@/components/valuecell/form";

export const { fieldContext, useFieldContext, formContext, useFormContext } =
  createFormHookContexts();
export const { useAppForm, withForm } = createFormHook({
  fieldComponents: {
    TextField,
  },
  formComponents: {},
  fieldContext,
  formContext,
});
