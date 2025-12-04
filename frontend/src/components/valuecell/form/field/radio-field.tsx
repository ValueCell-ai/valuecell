import type { FC, ReactNode } from "react";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { RadioGroup } from "@/components/ui/radio-group";
import { useFieldContext } from "@/hooks/use-form";

interface RadioFieldProps {
  label: string;
  children: ReactNode;
}

export const RadioField: FC<RadioFieldProps> = ({ label, children }) => {
  const field = useFieldContext<string>();

  return (
    <Field>
      <FieldLabel className="font-medium text-base text-gray-950">
        {label}
      </FieldLabel>
      <RadioGroup
        value={field.state.value}
        onValueChange={field.handleChange}
        className="flex items-center gap-6"
      >
        {children}
      </RadioGroup>
      <FieldError errors={field.state.meta.errors} />
    </Field>
  );
};
