import type { FC } from "react";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useFieldContext } from "@/hooks/use-form";
import { isNullOrUndefined } from "@/lib/utils";

type NumberFieldProps = {
  label: string;
  placeholder: string;
  className?: string;
};

export const NumberField: FC<NumberFieldProps> = ({
  label,
  placeholder,
  className,
}) => {
  const field = useFieldContext<number>();

  const displayValue = isNullOrUndefined(field.state.value)
    ? ""
    : String(field.state.value);

  return (
    <Field className={className}>
      <FieldLabel className="font-medium text-base text-gray-950">
        {label}
      </FieldLabel>
      <Input
        type="number"
        value={displayValue}
        onChange={(e) => {
          const inputValue = e.target.value;
          if (inputValue === "") {
            field.handleChange(0);
          } else {
            field.handleChange(+inputValue);
          }
        }}
        onBlur={field.handleBlur}
        placeholder={placeholder}
      />
      <FieldError errors={field.state.meta.errors} />
    </Field>
  );
};
