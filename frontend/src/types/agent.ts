// Agent communication types for SSE events and business logic

import type {
  AGENT_COMPONENT_TYPE,
  AGENT_MULTI_SECTION_COMPONENT_TYPE,
  AGENT_SECTION_COMPONENT_TYPE,
} from "@/constants/agent";

// Base event data structures
interface BaseEventData {
  role: "user" | "agent" | "system";
  conversation_id: string; // Top-level conversation session
  thread_id: string; // Message chain within conversation
  task_id: string; // Single agent execution unit
  item_id: string; // Minimum granular render level
  metadata: Partial<{
    task_title: string; // Title of the task
  }>;
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
  component_type: AgentComponentType;
  content: string;
}>;

export type AgentToolCallMessage = MessageWithPayload<{
  /**
   * @deprecated the tool call id is similar to the item_id
   */
  tool_call_id: string;
  tool_name: string;
  tool_call_result?: string;
}>;

type ChatMessage = AgentChunkMessage | AgentComponentMessage;

export type ChatItem = ChatMessage & {
  component_type: AgentComponentType;
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
  tool_call_started: AgentToolCallMessage;
  tool_call_completed: AgentToolCallMessage;

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

export type SectionComponentType =
  (typeof AGENT_SECTION_COMPONENT_TYPE)[number];
export type MultiSectionComponentType =
  (typeof AGENT_MULTI_SECTION_COMPONENT_TYPE)[number];
export type AgentComponentType = (typeof AGENT_COMPONENT_TYPE)[number];

export interface ConversationView {
  threads: Record<string, ThreadView>;
  /**
   * By component_type grouped sections
   * @description this is rendered outside of the threads (main section)
   */
  sections: Record<SectionComponentType, ThreadView>;
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
  display_name: string;
  enabled: boolean;
  agent_metadata: AgentMetadata;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface AgentViewProps {
  agentName: string;
}
