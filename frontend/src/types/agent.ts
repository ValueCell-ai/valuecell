// Agent communication types for SSE events and business logic

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

// Helper types to reduce repetition
type EventWithPayload<TEvent, TPayload> = TEvent & PayloadWrapper<TPayload>;
type MessageWithRole<TRole extends string, TPayload> = BaseEventData & {
  role: TRole;
} & PayloadWrapper<TPayload>;

// Agent SSE event mapping
export interface AgentEventMap {
  // Lifecycle Events
  conversation_started: Pick<BaseEventData, "conversation_id">;
  thread_started: Pick<BaseEventData, "thread_id">;
  done: Pick<BaseEventData, "conversation_id" | "thread_id">;

  // Content Streaming Events
  message_chunk: EventWithPayload<
    BaseEventData & { role?: "user" | "agent" | "system" },
    { content: string }
  >;
  message: EventWithPayload<BaseEventData, { content: string }>;

  // Component Generation
  component_generator: EventWithPayload<
    BaseEventData,
    {
      component_type: string;
      content: string;
    }
  >;

  // User Interaction
  plan_require_user_input: EventWithPayload<
    Pick<BaseEventData, "conversation_id" | "thread_id">,
    { content: string }
  >;

  // Tool Execution Lifecycle
  tool_call_started: EventWithPayload<
    BaseEventData,
    {
      tool_call_id: string;
      tool_name: string;
    }
  >;

  tool_call_completed: EventWithPayload<
    BaseEventData,
    {
      tool_call_id: string;
      tool_name: string;
      tool_call_result: string;
    }
  >;

  // Reasoning Process
  reasoning: EventWithPayload<BaseEventData, { content: string }>;
  reasoning_started: BaseEventData;
  reasoning_completed: BaseEventData;

  // Error Handling
  plan_failed: EventWithPayload<
    Pick<BaseEventData, "conversation_id" | "thread_id">,
    { content: string }
  >;
  task_failed: EventWithPayload<BaseEventData, { content: string }>;
}

// Final chat message shapes used by UI
export type AgentChunkMessage = MessageWithRole<
  "agent" | "user" | "system",
  { content: string }
>;

export type AgentComponentMessage = MessageWithRole<
  "agent",
  {
    component_type: string;
    content: string;
  }
>;

export type AgentToolCallStartedMessage = MessageWithRole<
  "agent",
  {
    tool_call_id: string;
    tool_name: string;
  }
>;

export type AgentToolCallCompletedMessage = MessageWithRole<
  "agent",
  {
    tool_call_id: string;
    tool_name: string;
    tool_call_result: string;
  }
>;

export type AgentReasoningMessage = MessageWithRole<
  "agent",
  { content: string }
>;

export type AgentPlanRequireUserInputMessage = {
  role: "agent";
} & Pick<BaseEventData, "conversation_id" | "thread_id"> &
  PayloadWrapper<{ content: string }>;

export type AgentPlanFailedMessage = AgentPlanRequireUserInputMessage;
export type AgentTaskFailedMessage = AgentPlanRequireUserInputMessage;

export type ChatMessage =
  | AgentComponentMessage
  | AgentToolCallStartedMessage
  | AgentToolCallCompletedMessage
  | AgentReasoningMessage
  | AgentChunkMessage
  | AgentPlanRequireUserInputMessage
  | AgentPlanFailedMessage
  | AgentTaskFailedMessage;

export interface ThreadView {
  messages: ChatMessage[];
}

export interface ConversationView {
  threads: Record<string, ThreadView>;
  currentThreadId?: string;
}

export type AgentConversationsStore = Record<string, ConversationView>;

// SSE data wrapper with strongly-typed Agent events (discriminated union)
export type SSEData = {
  [E in keyof AgentEventMap]: {
    /** Event type identifier */
    event: E;
    /** Event payload data */
    data: AgentEventMap[E];
  };
}[keyof AgentEventMap];

// Agent stream request
export type AgentStreamRequest = {
  query: string;
  agent_name: string;
} & Partial<Pick<BaseEventData, "conversation_id" | "thread_id">>;
