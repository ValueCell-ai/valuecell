import { parse } from "best-effort-json-parser";
import { Clock } from "lucide-react";
import { type FC, memo, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
    <div className="relative flex size-full items-center justify-between gap-3 rounded-xl bg-gray-50 px-4 py-3">
      {/* Left: Icon + Task Title */}
      <div className="flex shrink-0 items-center gap-3">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <Clock className="size-5 text-primary" />
        </div>
        <div className="flex flex-col items-start leading-snug">
          <p className="font-medium text-base text-gray-950">
            {task_title || "Untitled Task"}
          </p>
        </div>
      </div>

      {/* Right: Control Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={handleToggle}
        className={cn(
          "h-auto shrink-0 px-0 font-medium text-base hover:bg-transparent",
          isRunning
            ? "text-destructive hover:text-destructive/80"
            : "text-primary hover:text-primary/80",
        )}
      >
        {isRunning ? "Pause" : "Start"}
      </Button>
    </div>
  );
};

export default memo(ScheduledTaskControllerRenderer);
