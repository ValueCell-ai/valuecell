/**
 * Fetch-based SSE client library
 * Implements SSE using fetch + ReadableStream with custom headers, auto-reconnect, and type safety
 */

export interface SSEOptions {
  /** SSE endpoint URL */
  url: string;
  /** Custom request headers */
  headers?: Record<string, string>;
  /** Enable automatic reconnection */
  autoReconnect?: boolean;
  /** Reconnection interval in milliseconds */
  reconnectInterval?: number;
  /** Maximum number of reconnection attempts */
  maxReconnectAttempts?: number;
  /** Connection timeout in milliseconds */
  timeout?: number;
  /** Additional fetch request options */
  fetchOptions?: Omit<RequestInit, "method" | "body" | "headers" | "signal">;
}

export interface SSEEventHandlers<T = Record<string, unknown>> {
  /** Called when SSE data is received */
  onData?: (data: SSEData<T>) => void;
  /** Called when connection is established */
  onOpen?: () => void;
  /** Called when an error occurs */
  onError?: (error: Error) => void;
  /** Called when connection is closed */
  onClose?: () => void;
  /** Called during reconnection attempts */
  onReconnect?: (attempt: number) => void;
}

export enum SSEReadyState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSED = 2,
}

export class SSEClient<T = Record<string, unknown>> {
  private options: Required<SSEOptions>;
  private currentBody?: BodyInit;
  private handlers: SSEEventHandlers<T> = {};
  private reconnectCount = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isManualClose = false;
  private readyState: SSEReadyState = SSEReadyState.CLOSED;
  private abortController: AbortController | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  constructor(options: SSEOptions) {
    this.options = {
      autoReconnect: false,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      timeout: 30000,
      headers: {},
      fetchOptions: {},
      ...options,
    };
  }

  /**
   * Set event handlers for SSE events
   */
  setEventHandlers(handlers: SSEEventHandlers<T>): void {
    this.handlers = { ...this.handlers, ...handlers };
  }

  /**
   * Connect to the SSE endpoint
   */
  async connect(body?: BodyInit): Promise<void> {
    // Prevent duplicate connections
    if (this.readyState === SSEReadyState.CONNECTING) {
      console.log("Already connecting, ignoring duplicate connect request");
      return;
    }

    if (this.readyState === SSEReadyState.OPEN) {
      console.log(
        "Already connected, closing existing connection before reconnecting",
      );
      this.close();
    }

    this.currentBody = body;
    this.isManualClose = false;
    this.readyState = SSEReadyState.CONNECTING;
    this.abortController = new AbortController();

    try {
      await this.startConnection();
    } catch (error) {
      this.readyState = SSEReadyState.CLOSED;
      throw error;
    }
  }

  /**
   * Start the connection using fetch + ReadableStream
   */
  private async startConnection(): Promise<void> {
    let didTimeout = false;
    const timeoutId = setTimeout(() => {
      didTimeout = true;
      this.abortController?.abort();
    }, this.options.timeout);

    try {
      const response = await fetch(this.options.url, {
        method: "POST",
        body: this.currentBody,
        signal: this.abortController?.signal,
        ...this.options.fetchOptions,
        headers: {
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
          ...this.options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("Response body is empty");
      }

      // Connection established
      this.readyState = SSEReadyState.OPEN;
      this.reconnectCount = 0;
      this.handlers.onOpen?.();

      // Start reading the stream
      await this.readStream(response.body);
    } catch (error) {
      clearTimeout(timeoutId);
      this.readyState = SSEReadyState.CLOSED;

      if (error instanceof Error && error.name === "AbortError") {
        // Manual close: do not emit error or reconnect
        if (this.isManualClose) {
          return;
        }

        // Timeout: emit error and optionally reconnect based on config
        if (didTimeout) {
          const timeoutError = new Error("Connection timeout");
          this.handlers.onError?.(timeoutError);
          if (this.options.autoReconnect) {
            this.scheduleReconnect();
          }
          throw timeoutError;
        }

        // Other aborts (e.g., superseded by a new connect): treat as normal close
        this.handlers.onClose?.();
        return;
      }

      // Other network/HTTP errors
      this.handlers.onError?.(error as Error);
      if (!this.isManualClose && this.options.autoReconnect) {
        this.scheduleReconnect();
      }
      throw error;
    }
  }

  /**
   * Read the response stream and process SSE events
   */
  private async readStream(body: ReadableStream<Uint8Array>): Promise<void> {
    this.reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await this.reader.read();

        if (done) {
          this.readyState = SSEReadyState.CLOSED;
          if (!this.isManualClose && this.options.autoReconnect) {
            this.scheduleReconnect();
          } else {
            this.handlers.onClose?.();
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete event blocks
        let eventEnd: number = buffer.indexOf("\n\n");
        while (eventEnd !== -1) {
          const eventBlock = buffer.slice(0, eventEnd);
          buffer = buffer.slice(eventEnd + 2);

          if (eventBlock.trim()) {
            this.processEvent(eventBlock);
          }

          eventEnd = buffer.indexOf("\n\n");
        }
      }
    } catch (error) {
      this.readyState = SSEReadyState.CLOSED;

      if (!this.isManualClose) {
        this.handlers.onError?.(error as Error);

        if (this.options.autoReconnect) {
          this.scheduleReconnect();
        }
      }
    } finally {
      this.reader?.releaseLock();
      this.reader = null;
    }
  }

  /**
   * Process a single SSE event block
   */
  private processEvent(eventBlock: string): void {
    const lines = eventBlock.split("\n");
    let data = "";

    for (const line of lines) {
      if (line.startsWith("data:")) {
        data += `${line.slice(5).trim()}\n`;
      }
      // Ignore event: and retry: fields for simplicity
    }

    if (!data) return;

    // Remove trailing newline
    data = data.slice(0, -1);

    try {
      const parsedData = JSON.parse(data);

      // Pass through parsed payload without interpreting event names
      if (this.handlers.onData) {
        this.handlers.onData(parsedData as SSEData<T>);
      }
    } catch (error) {
      // Only log JSON parsing errors, don't trigger connection-level error handling
      console.warn("Failed to parse SSE message:", data, error);
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.isManualClose) return;
    // Check if already reconnecting
    if (this.reconnectTimer !== null) return;

    // Check if reached max attempts
    if (this.reconnectCount >= this.options.maxReconnectAttempts) {
      console.error(
        `SSE reconnection failed: reached max attempts (${this.options.maxReconnectAttempts})`,
      );
      this.handlers.onClose?.();
      return;
    }

    this.reconnectCount++;
    this.handlers.onReconnect?.(this.reconnectCount);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      console.log(`SSE reconnecting... (attempt ${this.reconnectCount})`);
      this.connect(this.currentBody).catch((error) => {
        console.error("Reconnection failed:", error);
      });
    }, this.options.reconnectInterval);
  }

  /**
   * Get current connection state
   */
  get state(): SSEReadyState {
    return this.readyState;
  }

  /**
   * Check if currently connected
   */
  get isConnected(): boolean {
    return this.readyState === SSEReadyState.OPEN;
  }

  /**
   * Check if currently connecting
   */
  get isConnecting(): boolean {
    return this.readyState === SSEReadyState.CONNECTING;
  }

  /**
   * Get number of reconnection attempts
   */
  get reconnectAttempts(): number {
    return this.reconnectCount;
  }

  /**
   * Close the SSE connection
   */
  close(): void {
    this.isManualClose = true;
    this.readyState = SSEReadyState.CLOSED;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    if (this.reader) {
      this.reader.cancel();
      this.reader = null;
    }

    this.handlers.onClose?.();
  }

  /**
   * Destroy the client instance and clean up all resources
   */
  destroy(): void {
    this.close();
    this.handlers = {};
    this.reconnectCount = 0;
  }
}

export default SSEClient;

import type { SSEData } from "@/types/agent";

/*
Usage Example:

import SSEClient from './sse-client';
import type { AgentEventMap, SSEData } from '@/types/agent';

// Create SSE client with type safety
const client = new SSEClient<AgentEventMap[keyof AgentEventMap]>({
  url: 'http://localhost:8080/api/chat/stream',
  headers: {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  autoReconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  timeout: 30000,
  fetchOptions: {
    credentials: 'include',
  },
});

// Set up event handlers with full type safety
client.setEventHandlers({
  onData: (sseData: SSEData<AgentEventMap[keyof AgentEventMap]>) => {
    // sseData contains { event: string, data: typed based on AgentEventMap }
    const { event, data } = sseData;
    
    switch (event) {
      case 'conversation_started':
        console.log(`Conversation started: ${data.conversation_id}`);
        break;
        
      case 'message_chunk':
      case 'message':
        console.log(`Message chunk: ${data.payload.content}`);
        appendToMessage(data.thread_id, data.payload.content);
        break;
        
      case 'component_generator':
        console.log(`Component generated: ${data.payload.component_type}`);
        renderComponent(data.payload.component_type, data.payload.content);
        break;
        
      case 'plan_require_user_input':
        console.log(`Plan requires user input: ${data.payload.content}`);
        showUserInputPrompt(data.payload.content);
        break;
        
      case 'tool_call_started':
        console.log(`Tool call started: ${data.payload.tool_name}`);
        showToolExecution(data.payload.tool_name, data.payload.tool_call_id);
        break;
        
      case 'tool_call_completed':
        console.log(`Tool call completed: ${data.payload.tool_call_id}`);
        updateToolResult(data.payload.tool_call_id, data.payload.tool_call_result);
        break;
        
      case 'reasoning':
        console.log(`Reasoning: ${data.payload.content}`);
        showReasoning(data.thread_id, data.payload.content);
        break;
        
      case 'reasoning_started':
        console.log(`Reasoning started for task: ${data.task_id}`);
        showReasoningIndicator(data.thread_id, true);
        break;
        
      case 'reasoning_completed':
        console.log(`Reasoning completed for task: ${data.task_id}`);
        showReasoningIndicator(data.thread_id, false);
        break;
        
      case 'plan_failed':
        console.log(`Plan failed: ${data.payload.content}`);
        showError('plan', data.payload.content);
        break;
        
      case 'task_failed':
        console.log(`Task failed: ${data.payload.content}`);
        showError('task', data.payload.content);
        break;
        
      case 'done':
        console.log(`Conversation ${data.conversation_id} completed`);
        markConversationComplete(data.conversation_id);
        break;
    }
  },
  onOpen: () => console.log('SSE connection established'),
  onError: (error) => console.error('SSE connection error:', error),
  onClose: () => console.log('SSE connection closed'),
  onReconnect: (attempt) => console.log(`Reconnecting (attempt ${attempt})`),
});

// Helper functions for UI updates
function appendToMessage(threadId: string, content: string) {
  const messageElement = document.getElementById(`thread-${threadId}`);
  if (messageElement) {
    messageElement.textContent += content;
  }
}

function renderComponent(componentType: string, content: string) {
  console.log(`Rendering component: ${componentType}`);
  // Implementation for rendering different component types
}

function showUserInputPrompt(content: string) {
  console.log(`User input required: ${content}`);
  // Show user input dialog
}

function showToolExecution(toolName: string, toolCallId: string) {
  console.log(`Executing tool: ${toolName} (ID: ${toolCallId})`);
}

function updateToolResult(toolCallId: string, result: string) {
  console.log(`Tool ${toolCallId} completed with result: ${result}`);
}

function showReasoning(threadId: string, reasoning: string) {
  console.log(`Reasoning for thread ${threadId}: ${reasoning}`);
}

function showReasoningIndicator(threadId: string, isActive: boolean) {
  console.log(`Reasoning indicator for thread ${threadId}: ${isActive ? 'active' : 'inactive'}`);
}

function showError(type: 'plan' | 'task', content: string) {
  console.error(`${type} error: ${content}`);
}

function markConversationComplete(conversationId: string) {
  console.log(`Conversation ${conversationId} is complete`);
}

// Connect to stream with POST body
const requestBody = JSON.stringify({
  message: 'Hello, how can you help me?',
  conversation_id: 123,
  // Add any other POST data you need
});

await client.connect(requestBody);

// Check connection status
console.log({
  isConnected: client.isConnected,
  isConnecting: client.isConnecting,
  reconnectAttempts: client.reconnectAttempts,
  state: client.state,
});

// Close connection when done
// client.close();

// Destroy instance to clean up resources
// client.destroy();
*/
