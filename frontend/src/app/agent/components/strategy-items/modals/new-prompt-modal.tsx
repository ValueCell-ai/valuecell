import { useForm } from "@tanstack/react-form";
import type { FC } from "react";
import { useState } from "react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
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
import CloseButton from "@/components/valuecell/button/close-button";

interface NewPromptModalProps {
  onSave: (value: { name: string; content: string }) => void;
  children: React.ReactNode;
}

// Schema for form validation
const promptSchema = z.object({
  name: z.string().min(1, "Prompt name is required"),
  content: z.string().min(1, "Prompt content is required"),
});

const NewPromptModal: FC<NewPromptModalProps> = ({ onSave, children }) => {
  const [open, setOpen] = useState(false);

  const form = useForm({
    defaultValues: {
      name: "",
      content: "",
    },
    validators: {
      onSubmit: promptSchema,
    },
    onSubmit: ({ value }) => {
      onSave(value);
      form.reset();
      setOpen(false);
    },
  });

  const handleCancel = () => {
    form.reset();
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="max-h-[90vh]" showCloseButton={false}>
        <DialogTitle className="flex items-center justify-between">
          <h2 className="font-medium text-gray-950 text-lg">
            Create New Prompt
          </h2>
          <CloseButton onClick={handleCancel} />
        </DialogTitle>

        {/* Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            form.handleSubmit();
          }}
        >
          <FieldGroup className="gap-6">
            {/* Prompt Name */}
            <form.Field name="name">
              {(field) => (
                <Field>
                  <FieldLabel className="font-medium text-base text-gray-950">
                    Prompt Name
                  </FieldLabel>
                  <Input
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    placeholder="Enter prompt name..."
                    className="rounded-xl border-gray-200"
                  />
                  <FieldError errors={field.state.meta.errors} />
                </Field>
              )}
            </form.Field>

            {/* Prompt Content */}
            <form.Field name="content">
              {(field) => (
                <Field>
                  <FieldLabel className="font-medium text-base text-gray-950">
                    Prompt Template
                  </FieldLabel>
                  <textarea
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    placeholder="Enter your prompt template..."
                    className="min-h-[300px] w-full resize-none rounded-xl border border-gray-200 p-4 text-sm placeholder:text-gray-400 focus:border-gray-300 focus:outline-none"
                  />
                  <FieldError errors={field.state.meta.errors} />
                </Field>
              )}
            </form.Field>
          </FieldGroup>

          {/* Footer */}
          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={handleCancel}
              className="rounded-xl border-gray-200 hover:bg-gray-50"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="rounded-xl bg-gray-950 hover:bg-gray-800"
            >
              Save Prompt
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default NewPromptModal;
