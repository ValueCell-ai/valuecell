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
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import CloseButton from "@/components/valuecell/button/close-button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";

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
  const [isSaving, setIsSaving] = useState(false);

  const form = useForm({
    defaultValues: {
      name: "",
      content: "",
    },
    validators: {
      onSubmit: promptSchema,
    },
    onSubmit: async ({ value }) => {
      setIsSaving(true);
      await onSave(value);
      setIsSaving(false);
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
      <DialogContent
        className="flex max-h-[90vh] flex-col"
        showCloseButton={false}
        aria-describedby={undefined}
      >
        <DialogTitle className="flex items-center justify-between font-medium text-gray-950 text-lg">
          Create New Prompt
          <CloseButton onClick={handleCancel} />
        </DialogTitle>

        <ScrollContainer>
          <form>
            <FieldGroup className="gap-6 py-2">
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
                    <Textarea
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      placeholder="Enter your prompt template..."
                      className="min-h-[300px]"
                    />
                    <FieldError errors={field.state.meta.errors} />
                  </Field>
                )}
              </form.Field>
            </FieldGroup>
          </form>
        </ScrollContainer>
        {/* Footer */}
        <div className="mt-auto flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={handleCancel}
            className="flex-1 py-4 font-semibold text-base"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            className="flex-1 py-4 font-semibold text-base text-white hover:bg-gray-800"
            onClick={form.handleSubmit}
            disabled={isSaving}
          >
            {isSaving && <Spinner />} Save Prompt
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default NewPromptModal;
