// Agent communication types for SSE events and business logic

// SSE data wrapper
export interface SSEData<T = Record<string, unknown>> {
  event: string;
  data: T;
}

// Base event data structures
interface BaseEventData {
  conversation_id: string; // Top-level conversation session
  thread_id: string; // Message chain within conversation
  task_id: string; // Single agent execution unit
  subtask_id: string; // Granular operation within task
}

// Payload wrapper for content events
interface PayloadWrapper<T> {
  payload: T;
}

// Agent SSE event mapping
export interface AgentEventMap {
  // Lifecycle Events
  conversation_started: Pick<BaseEventData, "conversation_id">;

  done: Pick<BaseEventData, "conversation_id" | "thread_id">;

  // Content Streaming Events
  message_chunk: BaseEventData &
    PayloadWrapper<{
      content: string;
    }>;

  message: BaseEventData &
    PayloadWrapper<{
      content: string;
    }>;

  // Component Generation
  component_generator: BaseEventData &
    PayloadWrapper<{
      component_type: string;
      content: string;
    }>;

  // User Interaction
  plan_require_user_input: Pick<
    BaseEventData,
    "conversation_id" | "thread_id"
  > &
    PayloadWrapper<{
      content: string;
    }>;

  // Tool Execution Lifecycle
  tool_call_started: BaseEventData &
    PayloadWrapper<{
      tool_call_id: string;
      tool_name: string;
    }>;

  tool_call_completed: BaseEventData &
    PayloadWrapper<{
      tool_call_id: string;
      tool_name: string;
      tool_call_result: string;
    }>;

  // Reasoning Process
  reasoning: BaseEventData &
    PayloadWrapper<{
      content: string;
    }>;

  reasoning_started: BaseEventData;
  reasoning_completed: BaseEventData;

  // Error Handling
  plan_failed: Pick<BaseEventData, "conversation_id" | "thread_id"> &
    PayloadWrapper<{
      content: string;
    }>;

  task_failed: BaseEventData &
    PayloadWrapper<{
      content: string;
    }>;
}

// Chat message with event data
export type ChatMessage<T extends keyof AgentEventMap> = {
  role: "user" | "system" | "agent";
  isComplete: boolean;
} & AgentEventMap[T];

// Agent stream request
export type AgentStreamRequest = {
  query: string;
  agent_name: string;
} & Partial<Pick<BaseEventData, "conversation_id" | "thread_id">>;
