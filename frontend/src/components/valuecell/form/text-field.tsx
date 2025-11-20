import type { FC } from "react";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useFieldContext } from "@/hooks/use-form";

interface TextFieldProps {
  label: string;
  placeholder: string;
}

export const TextField: FC<TextFieldProps> = ({ label, placeholder }) => {
  const field = useFieldContext<string | number>();

  return (
    <Field>
      <FieldLabel className="font-medium text-base text-gray-950">
        {label}
      </FieldLabel>
      <Input
        value={field.state.value}
        onChange={(e) => field.handleChange(e.target.value)}
        onBlur={field.handleBlur}
        placeholder={placeholder}
      />
      <FieldError errors={field.state.meta.errors} />
    </Field>
  );
};
