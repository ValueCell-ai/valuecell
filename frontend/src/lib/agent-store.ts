import { create } from "mutative";
import type {
  AgentConversationsStore,
  AgentEventMap,
  ConversationView,
  SSEData,
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
    conversation.threads[threadId] = { messages: [] };
  }
  conversation.currentThreadId = threadId;
  return conversation.threads[threadId];
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
  },

  message_chunk: (
    draft: AgentConversationsStore,
    data: AgentEventMap["message_chunk"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    thread.messages.push({ role: "agent", ...data });
  },

  message: (draft: AgentConversationsStore, data: AgentEventMap["message"]) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    thread.messages.push({ role: "agent", ...data });
  },

  reasoning: (
    draft: AgentConversationsStore,
    data: AgentEventMap["reasoning"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    thread.messages.push({ role: "agent", ...data });
  },

  tool_call_started: (
    draft: AgentConversationsStore,
    data: AgentEventMap["tool_call_started"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    thread.messages.push({
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
    thread.messages.push({ role: "agent", ...data });
  },

  component_generator: (
    draft: AgentConversationsStore,
    data: AgentEventMap["component_generator"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    thread.messages.push({ role: "agent", ...data });
  },

  plan_failed: (
    draft: AgentConversationsStore,
    data: AgentEventMap["plan_failed"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    const thread = ensureThread(conversation, data.thread_id);
    thread.messages.push({
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
    thread.messages.push({
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
    thread.messages.push({ role: "agent", ...data });
  },

  reasoning_started: (
    draft: AgentConversationsStore,
    data: AgentEventMap["reasoning_started"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    ensureThread(conversation, data.thread_id);
  },

  reasoning_completed: (
    draft: AgentConversationsStore,
    data: AgentEventMap["reasoning_completed"],
  ) => {
    const conversation = ensureConversation(draft, data.conversation_id);
    ensureThread(conversation, data.thread_id);
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
