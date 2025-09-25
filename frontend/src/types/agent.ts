// Agent communication types for SSE events and business logic

// Base event data structures
interface BaseEventData {
  role: "user" | "agent" | "system";
  conversation_id: string; // Top-level conversation session
  thread_id: string; // Message chain within conversation
  task_id: string; // Single agent execution unit
  item_id: string; // Minimum granular render level
}

// Helper types to reduce repetition
interface PayloadWrapper<T> {
  payload: T;
}
type MessageWithPayload<TPayload> = BaseEventData & PayloadWrapper<TPayload>;

// Final chat message shapes used by UI
export type AgentChunkMessage = MessageWithPayload<{ content: string }>;
export type AgentReasoningMessage = AgentChunkMessage;
export type AgentThreadStartedMessage = AgentChunkMessage;
export type AgentPlanRequireUserInputMessage = AgentChunkMessage;
export type AgentPlanFailedMessage = AgentChunkMessage;
export type AgentTaskFailedMessage = AgentChunkMessage;
export type AgentSystemFailedMessage = AgentChunkMessage;

export type AgentComponentMessage = MessageWithPayload<{
  component_type: string;
  content: string;
}>;

export type AgentToolCallStartedMessage = MessageWithPayload<{
  tool_call_id: string;
  tool_name: string;
}>;

export type AgentToolCallCompletedMessage = MessageWithPayload<{
  tool_call_id: string;
  tool_name: string;
  tool_call_result: string;
}>;

type ChatMessage =
  | AgentChunkMessage
  | AgentComponentMessage
  | AgentToolCallStartedMessage
  | AgentToolCallCompletedMessage;

export type ChatItem = ChatMessage & {
  component_type: string;
};

export interface AgentEventMap {
  // Lifecycle Events
  conversation_started: Pick<BaseEventData, "conversation_id">;
  thread_started: AgentThreadStartedMessage;
  done: Pick<BaseEventData, "conversation_id" | "thread_id">;

  // Content Streaming Events
  message_chunk: AgentChunkMessage;
  message: AgentChunkMessage;

  // Component Generation
  component_generator: AgentComponentMessage;

  // User Interaction
  plan_require_user_input: AgentPlanRequireUserInputMessage;

  // Tool Execution Lifecycle
  tool_call_started: AgentToolCallStartedMessage;

  tool_call_completed: AgentToolCallCompletedMessage;

  // Reasoning Process
  reasoning: AgentReasoningMessage;
  reasoning_started: BaseEventData;
  reasoning_completed: BaseEventData;

  // Error Handling
  plan_failed: AgentPlanFailedMessage;
  task_failed: AgentTaskFailedMessage;
  system_failed: AgentSystemFailedMessage;
}

export interface TaskView {
  items: ChatItem[];
}

export interface ThreadView {
  tasks: Record<string, TaskView>;
}

export interface ConversationView {
  threads: Record<string, ThreadView>;
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

export interface AgentMetadata {
  version: string;
  author: string;
  tags: string[];
}

export interface AgentInfo {
  agent_name: string;
  icon_url: string;
  enabled: boolean;
  agent_metadata: AgentMetadata;
  description: string;
  created_at: string;
  updated_at: string;
}
