import { type FC, memo } from "react";

const StreamingIndicator: FC = () => {
  return (
    <output
      className="flex items-center gap-2 text-gray-500 text-sm"
      aria-live="polite"
      aria-label="AI is thinking"
    >
      <div className="flex space-x-1" aria-hidden="true">
        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-0" />
        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-150" />
        <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-300" />
      </div>
      <span>AI is thinking...</span>
    </output>
  );
};

export default memo(StreamingIndicator);
