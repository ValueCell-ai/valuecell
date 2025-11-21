import { createFormHook, createFormHookContexts } from "@tanstack/react-form";
import {
  NumberField,
  RadioField,
  SelectField,
  TextField,
} from "@/components/valuecell/form";

export const { fieldContext, useFieldContext, formContext, useFormContext } =
  createFormHookContexts();
export const { useAppForm, withForm } = createFormHook({
  fieldComponents: {
    TextField,
    NumberField,
    SelectField,
    RadioField,
  },
  formComponents: {},
  fieldContext,
  formContext,
});
