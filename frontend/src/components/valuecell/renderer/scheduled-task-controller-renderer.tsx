import { parse } from "best-effort-json-parser";
import { Clock } from "lucide-react";
import { type FC, memo, useEffect, useState } from "react";
import { useCancelTask } from "@/api/conversation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ScheduledTaskControllerRendererProps } from "@/types/renderer";

const ScheduledTaskControllerRenderer: FC<
  ScheduledTaskControllerRendererProps
> = ({ content }) => {
  const { task_title, task_id, task_status } = parse(content);
  const [isRunning, setIsRunning] = useState(task_status === "running");
  const { mutateAsync: cancelTask } = useCancelTask();

  useEffect(() => {
    setIsRunning(task_status === "running");
  }, [task_status]);

  const handleCancel = async () => {
    const res = await cancelTask(task_id);
    res.code === 0 && setIsRunning(false);
  };

  return (
    <div className="flex min-w-96 items-center justify-between gap-3 rounded-xl bg-gray-50 px-4 py-3">
      <div className="flex shrink-0 items-center gap-3">
        <div className="flex size-8 shrink-0 items-center justify-center">
          <Clock className="size-5 text-primary" />
        </div>
        <p className="font-medium text-base text-gray-950">
          {task_title || "Untitled Task"}
        </p>
      </div>

      {/* Right: Control Text Button */}
      <Button
        onClick={handleCancel}
        variant="ghost"
        size="sm"
        disabled={!isRunning}
        className={cn(
          "cursor-pointer text-base text-blue-500 transition-colors hover:text-blue-500/80 disabled:text-gray-400",
        )}
      >
        {isRunning ? "Cancel" : "Cancelled"}
      </Button>
    </div>
  );
};

export default memo(ScheduledTaskControllerRenderer);
