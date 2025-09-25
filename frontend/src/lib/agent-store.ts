import { create } from "mutative";
import type {
  AgentConversationsStore,
  ChatItem,
  ConversationView,
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
  // Ensure conversation
  if (!draft[data.conversation_id]) {
    draft[data.conversation_id] = { threads: {} };
  }
  const conversation = draft[data.conversation_id];

  // Ensure thread
  if (!conversation.threads[data.thread_id]) {
    conversation.threads[data.thread_id] = { tasks: {} };
  }
  const thread = conversation.threads[data.thread_id];

  // Ensure task
  if (!thread.tasks[data.task_id]) {
    thread.tasks[data.task_id] = { items: [] };
  }
  const task = thread.tasks[data.task_id];

  return { conversation, thread, task };
}

// Helper function: find existing item by item_id in task
function findExistingItem(task: TaskView, itemId: string): number {
  return task.items.findIndex((item) => item.item_id === itemId);
}

// Check if item has mergeable content
function hasContent(
  item: ChatItem,
): item is ChatItem & { payload: { content: string } } {
  return "payload" in item && "content" in item.payload;
}

// Helper function: add or update item in task
function addOrUpdateItem(task: TaskView, newItem: ChatItem): void {
  const existingIndex = findExistingItem(task, newItem.item_id);

  if (existingIndex >= 0) {
    const existingItem = task.items[existingIndex];
    // Merge content for streaming events, replace for others
    if (hasContent(existingItem) && hasContent(newItem)) {
      existingItem.payload.content += newItem.payload.content;
    } else {
      task.items[existingIndex] = newItem;
    }
  } else {
    task.items.push(newItem);
  }
}

// Generic handler for events that create chat items
function handleChatItemEvent(draft: AgentConversationsStore, data: ChatItem) {
  const { task } = ensurePath(draft, data);
  addOrUpdateItem(task, data);
}

export function updateAgentConversationsStore(
  store: AgentConversationsStore,
  sseData: SSEData,
): AgentConversationsStore {
  const { event, data } = sseData;

  // Use mutative to create new state with type-safe event handling
  return create(store, (draft) => {
    switch (event) {
      case "thread_started":
      case "message_chunk":
      case "message":
      case "reasoning":
      case "tool_call_started":
      case "tool_call_completed":
      case "component_generator":
      case "task_failed":
      case "plan_failed":
      case "system_failed":
      case "plan_require_user_input":
        handleChatItemEvent(draft, { component_type: "markdown", ...data });
        break;

      case "reasoning_started":
      case "reasoning_completed":
        ensurePath(draft, data);
        break;

      default:
        break;
    }
  });
}
