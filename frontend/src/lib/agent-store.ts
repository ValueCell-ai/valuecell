import { create } from "mutative";
import { AGENT_SECTION_COMPONENT_TYPE } from "@/constants/agent";
import type {
  AgentConversationsStore,
  ChatItem,
  ConversationView,
  SectionComponentType,
  SSEData,
  TaskView,
  ThreadView,
} from "@/types/agent";

// Unified helper to ensure conversation->thread->task path exists
function ensurePath(
  draft: AgentConversationsStore,
  data: {
    conversation_id: string;
    thread_id: string;
    task_id: string;
  },
): {
  conversation: ConversationView;
  thread: ThreadView;
  task: TaskView;
} {
  // Ensure conversation with sections initialized
  draft[data.conversation_id] ??= {
    threads: {},
    sections: {} as Record<SectionComponentType, ThreadView>,
  };
  const conversation = draft[data.conversation_id];

  // Ensure thread
  conversation.threads[data.thread_id] ??= { tasks: {} };
  const thread = conversation.threads[data.thread_id];

  // Ensure task
  thread.tasks[data.task_id] ??= { items: [] };
  const task = thread.tasks[data.task_id];

  return { conversation, thread, task };
}

// Helper to ensure section->task path exists
function ensureSection(
  conversation: ConversationView,
  componentType: SectionComponentType,
  taskId: string,
): TaskView {
  conversation.sections[componentType] ??= { tasks: {} };
  conversation.sections[componentType].tasks[taskId] ??= { items: [] };

  return conversation.sections[componentType].tasks[taskId];
}

// Check if item has mergeable content
function hasContent(
  item: ChatItem,
): item is ChatItem & { payload: { content: string } } {
  return "payload" in item && "content" in item.payload;
}

// Mark a specific reasoning item as complete
function markReasoningComplete(task: TaskView, itemId: string): void {
  const existingIndex = task.items.findIndex((item) => item.item_id === itemId);
  if (existingIndex >= 0 && hasContent(task.items[existingIndex])) {
    try {
      const parsed = JSON.parse(task.items[existingIndex].payload.content);
      task.items[existingIndex].payload.content = JSON.stringify({
        ...parsed,
        isComplete: true,
      });
    } catch {
      // If parsing fails, just mark as complete
      task.items[existingIndex].payload.content = JSON.stringify({
        content: task.items[existingIndex].payload.content,
        isComplete: true,
      });
    }
  }
}

// Mark all reasoning items in a task as complete
function markAllReasoningComplete(task: TaskView): void {
  for (const item of task.items) {
    if (item.component_type === "reasoning" && hasContent(item)) {
      try {
        const parsed = JSON.parse(item.payload.content);
        if (!parsed.isComplete) {
          item.payload.content = JSON.stringify({
            ...parsed,
            isComplete: true,
          });
        }
      } catch {
        // Skip items that can't be parsed
      }
    }
  }
}

// Helper function: add or update item in task
function addOrUpdateItem(
  task: TaskView,
  newItem: ChatItem,
  event: "append" | "replace" | "append-reasoning",
): void {
  const existingIndex = task.items.findIndex(
    (item) => item.item_id === newItem.item_id,
  );

  if (existingIndex < 0) {
    task.items.push(newItem);
    return;
  }

  const existingItem = task.items[existingIndex];
  // Merge content for streaming events, replace for others
  if (event === "append" && hasContent(existingItem) && hasContent(newItem)) {
    existingItem.payload.content += newItem.payload.content;
  } else if (
    event === "append-reasoning" &&
    hasContent(existingItem) &&
    hasContent(newItem)
  ) {
    // Special handling for reasoning: parse JSON, append content, re-serialize
    try {
      const existingParsed = JSON.parse(existingItem.payload.content);
      const newParsed = JSON.parse(newItem.payload.content);
      existingItem.payload.content = JSON.stringify({
        content: (existingParsed.content ?? "") + (newParsed.content ?? ""),
        isComplete: newParsed.isComplete ?? false,
      });
    } catch {
      // Fallback to replace if parsing fails
      task.items[existingIndex] = newItem;
    }
  } else {
    task.items[existingIndex] = newItem;
  }
}

// Generic handler for events that create chat items
function handleChatItemEvent(
  draft: AgentConversationsStore,
  data: ChatItem,
  event: "append" | "replace" | "append-reasoning" = "append",
) {
  const { conversation, task } = ensurePath(draft, data);

  // Auto-maintain sections - only non-markdown types create independent sections
  const componentType = data.component_type;
  if (
    componentType &&
    AGENT_SECTION_COMPONENT_TYPE.includes(componentType as SectionComponentType)
  ) {
    const sectionTask = ensureSection(
      conversation,
      componentType as SectionComponentType,
      data.task_id,
    );
    addOrUpdateItem(sectionTask, data, event);
    return;
  }

  addOrUpdateItem(task, data, event);
}

// Core event processor - processes a single SSE event
function processSSEEvent(draft: AgentConversationsStore, sseData: SSEData) {
  const { event, data } = sseData;

  switch (event) {
    // component_generator preserves original component_type
    case "component_generator": {
      const component_type = data.payload.component_type;

      switch (component_type) {
        case "scheduled_task_result":
        case "subagent_conversation":
          handleChatItemEvent(
            draft,
            {
              ...data,
              component_type,
            },
            "replace",
          );
          break;
        default:
          handleChatItemEvent(draft, {
            ...data,
            component_type,
          });
          break;
      }
      break;
    }

    case "thread_started":
    case "message_chunk":
    case "message":
    case "task_failed":
    case "plan_failed":
    case "plan_require_user_input":
      // Other events are set as markdown type
      handleChatItemEvent(draft, { component_type: "markdown", ...data });
      break;

    case "reasoning":
      // Reasoning is streaming content that needs to be appended (like message_chunk)
      handleChatItemEvent(
        draft,
        {
          component_type: "reasoning",
          ...data,
          payload: {
            content: JSON.stringify({
              content: data.payload.content,
              isComplete: false,
            }),
          },
        },
        "append-reasoning",
      );
      break;

    case "reasoning_started":
      // Create initial reasoning item with empty content
      handleChatItemEvent(
        draft,
        {
          component_type: "reasoning",
          ...data,
          payload: {
            content: JSON.stringify({
              content: "",
              isComplete: false,
            }),
          },
        },
        "replace",
      );
      break;

    case "reasoning_completed": {
      // Mark reasoning as complete
      const { task } = ensurePath(draft, data);
      markReasoningComplete(task, data.item_id);
      break;
    }

    case "tool_call_started":
    case "tool_call_completed": {
      handleChatItemEvent(
        draft,
        {
          component_type: "tool_call",
          ...data,
          payload: {
            content: JSON.stringify(data.payload),
          },
        },
        "replace",
      );
      break;
    }

    default:
      break;
  }
}

export function updateAgentConversationsStore(
  store: AgentConversationsStore,
  sseData: SSEData,
) {
  // Use mutative to create new state with type-safe event handling
  return create(store, (draft) => {
    processSSEEvent(draft, sseData);
  });
}

/**
 * Batch update agent conversations store with multiple SSE events
 * @param store - Current agent conversations store
 * @param conversationId - The conversation ID to clear and update
 * @param sseDataList - Array of SSE events to process
 * @returns Updated store with all events processed atomically
 */
export function batchUpdateAgentConversationsStore(
  store: AgentConversationsStore,
  conversationId: string,
  sseDataList: SSEData[],
  clearHistory = false,
) {
  // Process all events in a single mutative transaction for better performance
  return create(store, (draft) => {
    // Clear existing data for this conversation
    if (clearHistory && draft[conversationId]) {
      delete draft[conversationId];
    }

    // Process all new events
    for (const sseData of sseDataList) {
      processSSEEvent(draft, sseData);
    }

    // Mark all reasoning items as complete after loading history
    // since the stream has already finished
    const conversation = draft[conversationId];
    if (conversation) {
      for (const thread of Object.values(conversation.threads)) {
        for (const task of Object.values(thread.tasks)) {
          markAllReasoningComplete(task);
        }
      }
    }
  });
}
