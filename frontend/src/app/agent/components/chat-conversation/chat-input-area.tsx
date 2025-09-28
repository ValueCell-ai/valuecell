import { ArrowUp } from "lucide-react";
import { type FC, memo } from "react";
import { Button } from "@/components/ui/button";
import ScrollTextarea from "@/components/valuecell/scroll/scroll-textarea";
import { cn } from "@/lib/utils";

interface ChatInputAreaProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => Promise<void>;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  variant?: "welcome" | "chat";
}

const ChatInputArea: FC<ChatInputAreaProps> = ({
  value,
  onChange,
  onSend,
  onKeyDown,
  placeholder = "Type your message...",
  disabled = false,
  className,
  variant = "chat",
}) => {
  const handleKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send message on Enter key (excluding Shift+Enter line breaks and IME composition state)
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      await onSend();
    }
    onKeyDown?.(e);
  };

  const handleSend = async () => {
    if (!value.trim() || disabled) return;
    await onSend();
  };

  const isWelcomeVariant = variant === "welcome";

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-2xl bg-white p-4",
        "border border-gray-200 shadow-[0px_4px_20px_8px_rgba(17,17,17,0.04)]",
        "focus-within:border-gray-300 focus-within:shadow-[0px_4px_20px_8px_rgba(17,17,17,0.08)]",
        isWelcomeVariant && "w-2/3 min-w-[600px]",
        !isWelcomeVariant && "w-full",
        className,
      )}
    >
      <ScrollTextarea
        value={value}
        onInput={(e) => onChange(e.currentTarget.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        maxHeight={120}
        minHeight={24}
        disabled={disabled}
      />
      <Button
        size="icon"
        className="size-8 cursor-pointer self-end rounded-full"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
      >
        <ArrowUp size={16} className="text-white" />
      </Button>
    </div>
  );
};

export default memo(ChatInputArea);
