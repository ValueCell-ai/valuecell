import type { FC } from "react";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import CloseButton from "@/components/valuecell/button/close-button";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import type { StrategyPrompt } from "@/types/strategy";

interface ViewStrategyModalProps {
  prompt?: StrategyPrompt;
  children: React.ReactNode;
}

const ViewStrategyModal: FC<ViewStrategyModalProps> = ({
  prompt,
  children,
}) => {
  if (!prompt) return null;

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent
        className="flex max-h-[90vh] flex-col"
        showCloseButton={false}
        aria-describedby={undefined}
      >
        <DialogTitle className="flex items-center justify-between font-medium text-gray-950 text-lg">
          {prompt.name}
          <DialogClose asChild>
            <CloseButton />
          </DialogClose>
        </DialogTitle>

        <ScrollContainer>
          <p className="whitespace-pre-line font-normal text-base text-gray-950 leading-relaxed tracking-wide">
            {prompt.content}
          </p>
        </ScrollContainer>
      </DialogContent>
    </Dialog>
  );
};

export default ViewStrategyModal;
