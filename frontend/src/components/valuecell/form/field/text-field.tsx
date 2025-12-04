import type { FC, InputHTMLAttributes } from "react";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useFieldContext } from "@/hooks/use-form";

type TextFieldProps = {
  label: string;
  placeholder: string;
  className?: string;
} & InputHTMLAttributes<HTMLInputElement>;

export const TextField: FC<TextFieldProps> = ({
  label,
  placeholder,
  className,
}) => {
  const field = useFieldContext<string>();

  return (
    <Field className={className}>
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
