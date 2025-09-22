// Updated Agent SSE Event Map based on new API specification
export interface AgentEventMap {
  conversation_started: {
    conversation_id: string;
  };
  message_chunk: {
    data: {
      content: string;
    };
    conversation_id: string;
    thread_id: string;
    task_id: string;
    subtask_id: string;
  };
  message: {
    data: {
      content: string;
    };
    conversation_id: string;
    thread_id: string;
    task_id: string;
    subtask_id: string;
  };
  component_generator: {
    data: {
      component_type: string;
      content: string;
    };
    conversation_id: string;
    thread_id: string;
    task_id: string;
    subtask_id: string;
  };
  plan_require_user_input: {
    data: {
      content: string;
    };
    conversation_id: string;
    thread_id: string;
  };
  tool_call_started: {
    data: {
      tool_call_id: string;
      tool_name: string;
    };
    conversation_id: string;
    thread_id: string;
    task_id: string;
    subtask_id: string;
  };
  tool_call_completed: {
    data: {
      tool_call_id: string;
      tool_name: string;
      tool_call_result: string;
    };
    conversation_id: string;
    thread_id: string;
    task_id: string;
    subtask_id: string;
  };
  reasoning: {
    data: {
      content: string;
    };
    conversation_id: string;
    thread_id: string;
    task_id: string;
    subtask_id: string;
  };
  plan_failed: {
    data: {
      content: string;
    };
    conversation_id: string;
    thread_id: string;
  };
  task_failed: {
    data: {
      content: string;
    };
    conversation_id: string;
    thread_id: string;
    task_id: string;
    sub_task_id: string;
  };
  done: {
    conversation_id: string;
    thread_id: string;
  };
}

// Updated constants
export const TOOL_CALL_STATUS = {
  STARTED: "started",
  COMPLETED: "completed",
} as const;

export const MESSAGE_TYPE = {
  USER: "user",
  ASSISTANT: "assistant",
  COMPONENT: "component",
  ERROR: "error",
} as const;

export const COMPONENT_TYPE = {
  REPORT: "report",
  CHART: "chart",
  TABLE: "table",
  ANALYSIS: "analysis",
} as const;

export type ToolCallStatus =
  (typeof TOOL_CALL_STATUS)[keyof typeof TOOL_CALL_STATUS];
export type MessageType = (typeof MESSAGE_TYPE)[keyof typeof MESSAGE_TYPE];
export type ComponentType =
  (typeof COMPONENT_TYPE)[keyof typeof COMPONENT_TYPE];

// Updated interfaces
export interface ToolCall {
  id: string;
  name: string;
  status: ToolCallStatus;
  result?: string;
  startTime: Date;
  endTime?: Date;
}

export interface GeneratedComponent {
  type: ComponentType;
  content: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  type: MessageType;
  isComplete: boolean;
  toolCalls?: ToolCall[];
  reasoning?: string;
  component?: GeneratedComponent;
  threadId?: string;
  taskId?: string;
  subtaskId?: string;
}

export interface AgentStreamRequest {
  query: string;
  agent_name: string;
  conversation_id?: string;
  thread_id?: string;
}
