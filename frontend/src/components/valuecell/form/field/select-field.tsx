import type { FC, ReactNode } from "react";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useFieldContext } from "@/hooks/use-form";

interface SelectFieldProps {
  label: string;
  children: ReactNode;
}

export const SelectField: FC<SelectFieldProps> = ({ label, children }) => {
  const field = useFieldContext<string>();

  return (
    <Field>
      <FieldLabel className="font-medium text-base text-gray-950">
        {label}
      </FieldLabel>
      <Select value={field.state.value} onValueChange={field.handleChange}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>{children}</SelectContent>
      </Select>
      <FieldError errors={field.state.meta.errors} />
    </Field>
  );
};
