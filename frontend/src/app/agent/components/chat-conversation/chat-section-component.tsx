import { type FC, memo, useMemo, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import BackButton from "@/components/valuecell/button/back-button";
import { MarkdownRenderer } from "@/components/valuecell/renderer";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
import { COMPONENT_RENDERER_MAP } from "@/constants/agent";
import type { SectionComponentType, TaskView, ThreadView } from "@/types/agent";

// define different component types and their specific rendering components
const ScheduledTaskResultComponent: FC<{ tasks: Record<string, TaskView> }> = ({
  tasks,
}) => {
  const [selectedItemContent, setSelectedItemContent] = useState<string>("");
  const Component = COMPONENT_RENDERER_MAP.scheduled_task_result;

  // Convert tasks object to array with task_id
  const taskList = useMemo(() => {
    return Object.entries(tasks).map(([taskId, taskView]) => {
      return {
        id: taskId,
        title: taskView.items[0]?.metadata?.task_title || `Task ${taskId}`,
        items: taskView.items,
      };
    });
  }, [tasks]);

  // Select the first task by default
  const [selectedTaskId, setSelectedTaskId] = useState<string>(
    taskList[0]?.id || "",
  );

  // Get items for the selected task
  const selectedItems = useMemo(() => {
    const selectedTask = taskList.find((task) => task.id === selectedTaskId);
    return selectedTask?.items || [];
  }, [taskList, selectedTaskId]);

  return selectedItemContent ? (
    <section className="flex flex-1 flex-col py-6">
      <BackButton className="mb-3" onClick={() => setSelectedItemContent("")} />
      <ScrollContainer className="flex-1">
        <MarkdownRenderer content={selectedItemContent} />
      </ScrollContainer>
    </section>
  ) : (
    <section className="flex flex-1 flex-col gap-5 py-6">
      {/* Task Selector */}
      {taskList.length > 0 && (
        <Select value={selectedTaskId} onValueChange={setSelectedTaskId}>
          <SelectTrigger className="rounded-lg bg-gray-200 p-1.5">
            <SelectValue placeholder="Select a task" />
          </SelectTrigger>
          <SelectContent>
            {taskList.map((task) => (
              <SelectItem key={task.id} value={task.id}>
                {task.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {/* render items */}
      <ScrollContainer className="flex-1">
        {selectedItems.length > 0 && (
          <div className="space-y-2.5">
            {selectedItems.map(
              (item) =>
                item.payload && (
                  <Component
                    key={item.item_id}
                    content={item.payload.content}
                    onOpen={(data) => setSelectedItemContent(data)}
                  />
                ),
            )}
          </div>
        )}
      </ScrollContainer>
    </section>
  );
};

const ModelTradeComponent: FC<{ tasks: Record<string, TaskView> }> = ({
  tasks,
}) => {
  const Component = COMPONENT_RENDERER_MAP.filtered_line_chart;

  // Flatten all tasks' items into a single array
  const items = Object.values(tasks).flatMap((task) => task.items);

  return (
    <ScrollContainer className="min-w-[540px] flex-1 px-4">
      {items.length > 0 && (
        <div className="h-full space-y-3 p-4">
          {items.map(
            (item) =>
              item.payload && (
                <Component key={item.item_id} content={item.payload.content} />
              ),
          )}
        </div>
      )}
    </ScrollContainer>
  );
};

const ModelTradeTableComponent: FC<{ tasks: Record<string, TaskView> }> = ({
  tasks,
}) => {
  const Component = COMPONENT_RENDERER_MAP.filtered_card_push_notification;

  // Flatten all tasks' items into a single array
  const items = Object.values(tasks).flatMap((task) => task.items);

  return (
    <ScrollContainer className="w-[404px] shrink-0 overflow-hidden px-4">
      {items.length > 0 && (
        <div className="space-y-3">
          {items.map(
            (item) =>
              item.payload && (
                <Component key={item.item_id} content={item.payload.content} />
              ),
          )}
        </div>
      )}
    </ScrollContainer>
  );
};

// component mapping table
const SECTION_COMPONENT_MAP: Record<
  SectionComponentType,
  FC<{ tasks: Record<string, TaskView> }>
> = {
  scheduled_task_result: ScheduledTaskResultComponent,
  filtered_line_chart: ModelTradeComponent,
  filtered_card_push_notification: ModelTradeTableComponent,
};

interface ChatSectionComponentProps {
  componentType: SectionComponentType;
  threadView: ThreadView;
}

/**
 * dynamic component renderer
 * @description dynamically select the appropriate component to render based on componentType
 */
const ChatSectionComponent: FC<ChatSectionComponentProps> = ({
  componentType,
  threadView,
}) => {
  const Component = SECTION_COMPONENT_MAP[componentType];

  return <Component tasks={threadView.tasks} />;
};

export default memo(ChatSectionComponent);
