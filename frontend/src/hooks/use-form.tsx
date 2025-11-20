import { createFormHook, createFormHookContexts } from "@tanstack/react-form";
import { SelectField, TextField } from "@/components/valuecell/form";

export const { fieldContext, useFieldContext, formContext, useFormContext } =
  createFormHookContexts();
export const { useAppForm, withForm } = createFormHook({
  fieldComponents: {
    TextField,
    SelectField,
  },
  formComponents: {},
  fieldContext,
  formContext,
});
