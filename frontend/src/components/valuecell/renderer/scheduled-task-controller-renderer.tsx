import { parse } from "best-effort-json-parser";
import { Clock } from "lucide-react";
import { type FC, memo, useState } from "react";
import type { ScheduledTaskControllerRendererProps } from "@/types/renderer";

const ScheduledTaskControllerRenderer: FC<
  ScheduledTaskControllerRendererProps
> = ({ content }) => {
  const { task_title, task_id } = parse(content);
  const [isRunning, setIsRunning] = useState(false);

  const handleToggle = () => {
    // TODO: Implement actual task control logic with task_id
    console.log(`Toggling task ${task_id}:`, isRunning ? "pause" : "start");
    setIsRunning(!isRunning);
  };

  return (
    <div className="flex min-w-96 items-center justify-between gap-3 rounded-xl bg-gray-50 px-4 py-3">
      <div className="flex shrink-0 items-center gap-3">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Clock className="size-5 text-primary" />
        </div>
        <p className="font-medium text-base text-gray-950">
          {task_title || "Untitled Task"}
        </p>
      </div>

      {/* Right: Control Text Button */}
      <p
        onClick={handleToggle}
        className="cursor-pointer text-base text-blue-500 transition-colors hover:text-blue-500/80"
      >
        Pause
      </p>
    </div>
  );
};

export default memo(ScheduledTaskControllerRenderer);
