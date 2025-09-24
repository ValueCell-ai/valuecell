import { useCallback, useImperativeHandle, useRef } from "react";
import { cn } from "@/lib/utils";
import ScrollContainer from "./scroll-container";

export interface ScrollTextareaProps
  extends Omit<
    React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    "style" | "onChange"
  > {
  /**
   * Maximum height in pixels for the textarea container
   * @default 120
   */
  maxHeight?: number;
  /**
   * Minimum height in pixels for the textarea
   * @default 24
   */
  minHeight?: number;
  /**
   * Additional className for the ScrollContainer wrapper
   */
  containerClassName?: string;
  /**
   * Whether to auto-resize the textarea based on content
   * @default true
   */
  autoResize?: boolean;
  /**
   * Ref object to access textarea methods
   */
  ref?: React.Ref<ScrollTextareaRef>;
}

export interface ScrollTextareaRef {
  /**
   * Focus the textarea
   */
  focus: () => void;
  /**
   * Get the current textarea value
   */
  getValue: () => string;
}

function ScrollTextarea({
  className,
  containerClassName,
  maxHeight = 120,
  minHeight = 24,
  autoResize = true,
  onInput,
  ref,
  ...props
}: ScrollTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea function
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea || !autoResize) return;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = "auto";
    textarea.style.height = `${Math.max(textarea.scrollHeight, minHeight)}px`;
  }, [autoResize, minHeight]);

  // Handle input events (for compatibility)
  const handleInput = useCallback(
    (e: React.FormEvent<HTMLTextAreaElement>) => {
      onInput?.(e);
      // Note: onChange will handle the height adjustment
      adjustTextareaHeight();
    },
    [onInput, adjustTextareaHeight],
  );

  // Expose methods through ref
  useImperativeHandle(ref, () => ({
    focus: () => {
      textareaRef.current?.focus();
    },
    getValue: () => {
      return textareaRef.current?.value || "";
    },
  }));

  return (
    <ScrollContainer
      className={containerClassName}
      style={{ maxHeight: `${maxHeight}px` }}
    >
      <textarea
        ref={textareaRef}
        onInput={handleInput}
        className={cn(
          "w-full resize-none border-0 bg-transparent p-0 text-base leading-5.5 outline-none placeholder:text-gray-400",
          className,
        )}
        {...props}
      />
    </ScrollContainer>
  );
}

export default ScrollTextarea;
