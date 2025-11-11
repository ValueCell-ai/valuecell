import { X } from "lucide-react";
import type { FC } from "react";
import { Button } from "@/components/ui/button";

interface CloseButtonProps {
  onClick?: () => void;
}

const CloseButton: FC<CloseButtonProps> = ({ onClick }) => {
  return (
    <Button variant="ghost" size="icon" onClick={onClick}>
      <X />
    </Button>
  );
};

export default CloseButton;
