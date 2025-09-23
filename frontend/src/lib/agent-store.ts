import type {
  AgentComponentMessage,
  AgentConversationsStore,
  AgentEventMap,
  AgentReasoningMessage,
  AgentSSE,
  AgentTextMessage,
  AgentToolCallMessage,
  ChatMessage,
  ConversationView,
  SystemMessage,
  ThreadView,
} from "@/types/agent";

type AnyAgentEvent = AgentSSE;

function cloneThread(thread: ThreadView): ThreadView {
  return {
    ...thread,
    messages: [...thread.messages],
  };
}

function ensureConversation(
  store: AgentConversationsStore,
  conversationId: string,
): [AgentConversationsStore, ConversationView] {
  const existing = store[conversationId];
  if (!existing) {
    const next: AgentConversationsStore = { ...store };
    const conversation: ConversationView = { threads: {} };
    next[conversationId] = conversation;
    return [next, conversation];
  }
  // Shallow clone to preserve immutability
  const next: AgentConversationsStore = { ...store };
  const conversation: ConversationView = {
    ...existing,
    threads: { ...existing.threads },
  };
  next[conversationId] = conversation;
  return [next, conversation];
}

function ensureThread(
  conversation: ConversationView,
  threadId: string,
): [ConversationView, ThreadView] {
  const existing = conversation.threads[threadId];
  if (!existing) {
    const thread: ThreadView = { messages: [], status: "idle" };
    const nextConversation: ConversationView = {
      ...conversation,
      threads: { ...conversation.threads, [threadId]: thread },
      currentThreadId: threadId,
    };
    return [nextConversation, thread];
  }
  const clonedThread = cloneThread(existing);
  const nextConversation: ConversationView = {
    ...conversation,
    threads: { ...conversation.threads, [threadId]: clonedThread },
    currentThreadId: threadId,
  };
  return [nextConversation, clonedThread];
}

function isAgentTextMessage(msg: ChatMessage): msg is AgentTextMessage {
  return msg.role === "agent" && "payload" in msg;
}

function isAgentToolCallMessage(msg: ChatMessage): msg is AgentToolCallMessage {
  return msg.role === "agent" && "toolCall" in msg;
}

function isAgentReasoningMessage(
  msg: ChatMessage,
): msg is AgentReasoningMessage {
  return msg.role === "agent" && "reasoning" in msg;
}

function findLastOpenAgentTextIndex(
  messages: ChatMessage[],
  taskId: string,
  subtaskId?: string,
): number {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (!isAgentTextMessage(m)) continue;
    if (m.task_id !== taskId) continue;
    if (typeof subtaskId === "string" && m.subtask_id !== subtaskId) continue;
    if (m.isComplete) continue;
    return i;
  }
  return -1;
}

function pushToolCall(
  thread: ThreadView,
  payload:
    | AgentEventMap["tool_call_started"]
    | AgentEventMap["tool_call_completed"],
  status: "started" | "completed",
): void {
  const now = new Date();
  const msg: AgentToolCallMessage = {
    role: "agent",
    isComplete: status === "completed",
    createdAt: now,
    updatedAt: now,
    conversation_id: payload.conversation_id,
    thread_id: payload.thread_id,
    task_id: payload.task_id,
    subtask_id: payload.subtask_id,
    toolCall: {
      id: payload.payload.tool_call_id,
      name: payload.payload.tool_name,
      status,
      startTime: now,
      ...(status === "completed"
        ? {
            result: (payload as AgentEventMap["tool_call_completed"]).payload
              .tool_call_result,
            endTime: now,
          }
        : {}),
    },
  };
  thread.messages.push(msg);
}

function updateToolCallCompleted(
  thread: ThreadView,
  payload: AgentEventMap["tool_call_completed"],
): boolean {
  for (let i = thread.messages.length - 1; i >= 0; i -= 1) {
    const m = thread.messages[i];
    if (!isAgentToolCallMessage(m)) continue;
    if (m.toolCall.id !== payload.payload.tool_call_id) continue;
    m.toolCall.status = "completed";
    m.toolCall.result = payload.payload.tool_call_result;
    m.toolCall.endTime = new Date();
    m.isComplete = true;
    m.updatedAt = new Date();
    return true;
  }
  return false;
}

function pushAgentText(
  thread: ThreadView,
  base: Pick<
    AgentEventMap["message_chunk"],
    "conversation_id" | "thread_id" | "task_id" | "subtask_id"
  >,
  content: string,
  isComplete: boolean,
): void {
  const msg: AgentTextMessage = {
    role: "agent",
    isComplete,
    createdAt: new Date(),
    updatedAt: new Date(),
    conversation_id: base.conversation_id,
    thread_id: base.thread_id,
    task_id: base.task_id,
    subtask_id: base.subtask_id,
    payload: { content },
  };
  thread.messages.push(msg);
}

function pushAgentComponent(
  thread: ThreadView,
  payload: AgentEventMap["component_generator"],
): void {
  const msg: AgentComponentMessage = {
    role: "agent",
    isComplete: true,
    createdAt: new Date(),
    updatedAt: new Date(),
    conversation_id: payload.conversation_id,
    thread_id: payload.thread_id,
    task_id: payload.task_id,
    subtask_id: payload.subtask_id,
    component: {
      type: payload.payload.component_type,
      content: payload.payload.content,
    },
  };
  thread.messages.push(msg);
}

function pushSystemMessage(
  thread: ThreadView,
  partial: {
    conversation_id?: string;
    thread_id?: string;
    task_id?: string;
    subtask_id?: string;
    content: string;
  },
): void {
  const msg: SystemMessage = {
    role: "system",
    isComplete: true,
    createdAt: new Date(),
    updatedAt: new Date(),
    payload: { content: partial.content },
    ...(partial.conversation_id
      ? { conversation_id: partial.conversation_id }
      : {}),
    ...(partial.thread_id ? { thread_id: partial.thread_id } : {}),
    ...(partial.task_id ? { task_id: partial.task_id } : {}),
    ...(partial.subtask_id ? { subtask_id: partial.subtask_id } : {}),
  };
  thread.messages.push(msg);
}

// (Removed) ensureTextHostMessage is no longer needed after splitting message kinds

function findLastOpenReasoningIndex(
  thread: ThreadView,
  taskId: string,
  subtaskId?: string,
): number {
  for (let i = thread.messages.length - 1; i >= 0; i -= 1) {
    const m = thread.messages[i];
    if (!isAgentReasoningMessage(m)) continue;
    if (m.task_id !== taskId) continue;
    if (typeof subtaskId === "string" && m.subtask_id !== subtaskId) continue;
    if (m.isComplete) continue;
    return i;
  }
  return -1;
}

function pushReasoning(
  thread: ThreadView,
  base: Pick<
    AgentEventMap["reasoning"],
    "conversation_id" | "thread_id" | "task_id" | "subtask_id"
  >,
  content: string,
  isComplete: boolean,
): void {
  const now = new Date();
  const msg: AgentReasoningMessage = {
    role: "agent",
    isComplete,
    createdAt: now,
    updatedAt: now,
    conversation_id: base.conversation_id,
    thread_id: base.thread_id,
    task_id: base.task_id,
    subtask_id: base.subtask_id,
    reasoning: content,
  };
  thread.messages.push(msg);
}

export function updateAgentConversationsStore(
  store: AgentConversationsStore,
  sse: AnyAgentEvent,
): AgentConversationsStore {
  const { event } = sse;
  const data = sse.data as AgentEventMap[keyof AgentEventMap];

  switch (event) {
    case "conversation_started": {
      const { conversation_id } = data as AgentEventMap["conversation_started"];
      const [store2] = ensureConversation(store, conversation_id);
      return store2;
    }

    case "done": {
      const { conversation_id, thread_id } = data as AgentEventMap["done"];
      const [store2, conv] = ensureConversation(store, conversation_id);
      const [conv2, thread] = ensureThread(conv, thread_id);
      thread.status = "done";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [conversation_id]: conv2,
      };
      return next;
    }

    case "message_chunk": {
      const payload = data as AgentEventMap["message_chunk"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);

      const idx = findLastOpenAgentTextIndex(
        thread.messages,
        payload.task_id,
        payload.subtask_id,
      );
      if (idx === -1) {
        pushAgentText(
          thread,
          {
            conversation_id: payload.conversation_id,
            thread_id: payload.thread_id,
            task_id: payload.task_id,
            subtask_id: payload.subtask_id,
          },
          payload.payload.content,
          false,
        );
      } else {
        const msg = thread.messages[idx] as AgentTextMessage;
        msg.payload = {
          content: `${msg.payload.content}${payload.payload.content}`,
        };
        msg.isComplete = false;
        msg.updatedAt = new Date();
      }

      thread.status = "streaming";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "message": {
      const payload = data as AgentEventMap["message"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);

      const idx = findLastOpenAgentTextIndex(
        thread.messages,
        payload.task_id,
        payload.subtask_id,
      );
      if (idx === -1) {
        pushAgentText(
          thread,
          {
            conversation_id: payload.conversation_id,
            thread_id: payload.thread_id,
            task_id: payload.task_id,
            subtask_id: payload.subtask_id,
          },
          payload.payload.content,
          true,
        );
      } else {
        const msg = thread.messages[idx] as AgentTextMessage;
        msg.payload = { content: payload.payload.content };
        msg.isComplete = true;
        msg.updatedAt = new Date();
      }

      // After final message we set to idle; "done" will set to done
      thread.status = "idle";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "reasoning": {
      const payload = data as AgentEventMap["reasoning"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);

      const idx = findLastOpenReasoningIndex(
        thread,
        payload.task_id,
        payload.subtask_id,
      );
      if (idx === -1) {
        pushReasoning(
          thread,
          {
            conversation_id: payload.conversation_id,
            thread_id: payload.thread_id,
            task_id: payload.task_id,
            subtask_id: payload.subtask_id,
          },
          payload.payload.content,
          false,
        );
      } else {
        const msg = thread.messages[idx] as AgentReasoningMessage;
        msg.reasoning = `${msg.reasoning}${payload.payload.content}`;
        msg.isComplete = false;
        msg.updatedAt = new Date();
      }

      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "tool_call_started": {
      const payload = data as AgentEventMap["tool_call_started"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      pushToolCall(thread, payload, "started");
      thread.status = "streaming";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "tool_call_completed": {
      const payload = data as AgentEventMap["tool_call_completed"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      const updated = updateToolCallCompleted(thread, payload);
      if (!updated) {
        pushToolCall(thread, payload, "completed");
      }
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "component_generator": {
      const payload = data as AgentEventMap["component_generator"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      pushAgentComponent(thread, payload);
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "plan_failed": {
      const payload = data as AgentEventMap["plan_failed"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      pushSystemMessage(thread, {
        conversation_id: payload.conversation_id,
        thread_id: payload.thread_id,
        content: payload.payload.content,
      });
      thread.status = "idle";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "task_failed": {
      const payload = data as AgentEventMap["task_failed"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      pushSystemMessage(thread, {
        conversation_id: payload.conversation_id,
        thread_id: payload.thread_id,
        task_id: payload.task_id,
        subtask_id: payload.subtask_id,
        content: payload.payload.content,
      });
      thread.status = "idle";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "plan_require_user_input": {
      const payload = data as AgentEventMap["plan_require_user_input"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      thread.status = "awaiting_user";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "reasoning_started": {
      const payload = data as AgentEventMap["reasoning_started"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      thread.status = "streaming";
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    case "reasoning_completed": {
      const payload = data as AgentEventMap["reasoning_completed"];
      const [store2, conv] = ensureConversation(store, payload.conversation_id);
      const [conv2, thread] = ensureThread(conv, payload.thread_id);
      // Keep status unchanged; it may still be streaming for message/tool calls
      thread.lastUpdated = Date.now();
      const next: AgentConversationsStore = {
        ...store2,
        [payload.conversation_id]: conv2,
      };
      return next;
    }

    default:
      return store;
  }
}

export function createEmptyConversationsStore(): AgentConversationsStore {
  return {};
}
