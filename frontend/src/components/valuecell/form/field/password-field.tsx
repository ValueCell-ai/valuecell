import { Eye, EyeOff } from "lucide-react";
import { type FC, type InputHTMLAttributes, useState } from "react";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group";
import { useFieldContext } from "@/hooks/use-form";

type PasswordFieldProps = {
  label: string;
  placeholder: string;
  className?: string;
} & InputHTMLAttributes<HTMLInputElement>;

export const PasswordField: FC<PasswordFieldProps> = ({
  label,
  placeholder,
  className,
}) => {
  const field = useFieldContext<string>();
  const [showPassword, setShowPassword] = useState(false);

  return (
    <Field className={className}>
      <FieldLabel className="font-medium text-base text-gray-950">
        {label}
      </FieldLabel>
      <InputGroup>
        <InputGroupInput
          type={showPassword ? "text" : "password"}
          placeholder={placeholder}
          value={field.state.value}
          onChange={(e) => field.handleChange(e.target.value)}
          onBlur={field.handleBlur}
        />
        <InputGroupAddon align="inline-end" className="mr-0!">
          <InputGroupButton
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <EyeOff /> : <Eye />}
          </InputGroupButton>
        </InputGroupAddon>
      </InputGroup>
      <FieldError errors={field.state.meta.errors} />
    </Field>
  );
};
