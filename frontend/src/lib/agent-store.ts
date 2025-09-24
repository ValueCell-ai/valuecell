import { create } from "mutative";
import type {
  AgentConversationsStore,
  AgentEventMap,
  ChatItem,
  ConversationView,
  SSEData,
  TaskView,
  ThreadView,
} from "@/types/agent";

// Helper function: ensure conversation exists (for mutative draft)
function ensureConversation(
  draft: AgentConversationsStore,
  conversationId: string,
): ConversationView {
  if (!draft[conversationId]) {
    draft[conversationId] = { threads: {} };
  }
  return draft[conversationId];
}

// Helper function: ensure thread exists (for mutative draft)
function ensureThread(
  conversation: ConversationView,
  threadId: string,
): ThreadView {
  if (!conversation.threads[threadId]) {
    conversation.threads[threadId] = { tasks: {} };
  }
  conversation.currentThreadId = threadId;
  return conversation.threads[threadId];
}

// Helper function: ensure task exists (for mutative draft)
function ensureTask(thread: ThreadView, taskId: string): TaskView {
  if (!thread.tasks[taskId]) {
    thread.tasks[taskId] = { items: [] };
  }
  thread.currentTaskId = taskId;
  return thread.tasks[taskId];
}

// Helper function: find existing item by item_id in task
function findExistingItem(task: TaskView, itemId: string): number {
  return task.items.findIndex((item) => item.item_id === itemId);
}

// Helper function: add or update item in task
function addOrUpdateItem(task: TaskView, newItem: ChatItem): void {
  const existingIndex = findExistingItem(task, newItem.item_id);

  if (existingIndex >= 0) {
    // Item exists, merge content if it's a content-based event
    const existingItem = task.items[existingIndex];
    if (
      "payload" in newItem &&
      "content" in newItem.payload &&
      "payload" in existingItem &&
      "content" in existingItem.payload
    ) {
      // Concatenate content for streaming events like message_chunk
      existingItem.payload.content += newItem.payload.content;
    } else {
      // Replace item for non-content events
      task.items[existingIndex] = newItem;
    }
  } else {
    // Item doesn't exist, add new item
    task.items.push(newItem);
  }
}

// Event handlers: one handler function per event type
const eventHandlers = {
  conversation_started: (
    draft: AgentConversationsStore,
    data: AgentEventMap["conversation_started"],
  ) => {
    ensureConversation(draft, data.conversation_id);
  },

  done: (draft: AgentConversationsStore, data: AgentEventMap["done"]) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    ensureThread(conversation, data.thread_id);
    // done events don't have task_id, so we don't need to ensure task
  },

  message_chunk: (
    draft: AgentConversationsStore,
    data: AgentEventMap["message_chunk"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    const task = ensureTask(thread, data.task_id);
    addOrUpdateItem(task, { role: "agent", ...data });
  },

  message: (draft: AgentConversationsStore, data: AgentEventMap["message"]) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    const task = ensureTask(thread, data.task_id);
    addOrUpdateItem(task, { role: "agent", ...data });
  },

  reasoning: (
    draft: AgentConversationsStore,
    data: AgentEventMap["reasoning"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    const task = ensureTask(thread, data.task_id);
    addOrUpdateItem(task, { role: "agent", ...data });
  },

  tool_call_started: (
    draft: AgentConversationsStore,
    data: AgentEventMap["tool_call_started"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    const task = ensureTask(thread, data.task_id);
    addOrUpdateItem(task, {
      role: "agent",
      ...data,
    });
  },

  tool_call_completed: (
    draft: AgentConversationsStore,
    data: AgentEventMap["tool_call_completed"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    const task = ensureTask(thread, data.task_id);
    addOrUpdateItem(task, { role: "agent", ...data });
  },

  component_generator: (
    draft: AgentConversationsStore,
    data: AgentEventMap["component_generator"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    const task = ensureTask(thread, data.task_id);
    addOrUpdateItem(task, { role: "agent", ...data });
  },

  plan_failed: (
    draft: AgentConversationsStore,
    data: AgentEventMap["plan_failed"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    // plan_failed events don't have task_id, use empty string as default
    const task = ensureTask(thread, "");
    addOrUpdateItem(task, {
      role: "agent",
      ...data,
    });
  },

  plan_require_user_input: (
    draft: AgentConversationsStore,
    data: AgentEventMap["plan_require_user_input"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    // plan_require_user_input events don't have task_id, use empty string as default
    const task = ensureTask(thread, "");
    addOrUpdateItem(task, {
      role: "agent",
      ...data,
    });
  },

  task_failed: (
    draft: AgentConversationsStore,
    data: AgentEventMap["task_failed"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    const task = ensureTask(thread, data.task_id);
    addOrUpdateItem(task, { role: "agent", ...data });
  },

  reasoning_started: (
    draft: AgentConversationsStore,
    data: AgentEventMap["reasoning_started"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    ensureTask(thread, data.task_id);
  },

  reasoning_completed: (
    draft: AgentConversationsStore,
    data: AgentEventMap["reasoning_completed"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    ensureTask(thread, data.task_id);
  },
};

export function updateAgentConversationsStore(
  store: AgentConversationsStore,
  sseData: SSEData,
): AgentConversationsStore {
  const { event, data } = sseData;
  const handler = eventHandlers[event as keyof typeof eventHandlers];

  if (!handler) {
    return store; // Unknown event, return original state
  }

  // Use mutative to create new state, reduced from 250 lines to 10 lines
  return create(store, (draft) => {
    // Type-safe event handling: SSEData guarantees event and data types match
    (
      handler as (draft: AgentConversationsStore, data: SSEData["data"]) => void
    )(draft, data);
  });
}
