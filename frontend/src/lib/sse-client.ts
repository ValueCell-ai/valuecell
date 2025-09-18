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
  fetchOptions?: Omit<RequestInit, "headers" | "signal">;
}

export interface SSEEventHandlers<TEventMap = Record<string, unknown>> {
  /** Called when an event is received */
  onEvent?: <K extends keyof TEventMap>(
    eventType: K,
    data: TEventMap[K],
  ) => void;
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

export class SSEClient<TEventMap = Record<string, unknown>> {
  private options: Required<SSEOptions>;
  private handlers: SSEEventHandlers<TEventMap> = {};
  private reconnectCount = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isManualClose = false;
  private readyState: SSEReadyState = SSEReadyState.CLOSED;
  private abortController: AbortController | null = null;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  constructor(options: SSEOptions) {
    this.options = {
      autoReconnect: true,
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
  setEventHandlers(handlers: SSEEventHandlers<TEventMap>): void {
    this.handlers = { ...this.handlers, ...handlers };
  }

  /**
   * Connect to the SSE endpoint
   */
  async connect(): Promise<void> {
    if (this.readyState !== SSEReadyState.CLOSED) {
      return;
    }

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
    const timeoutId = setTimeout(() => {
      this.abortController?.abort();
    }, this.options.timeout);

    try {
      const response = await fetch(this.options.url, {
        method: "GET",
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
        const timeoutError = new Error("Connection timeout");
        this.handlers.onError?.(timeoutError);
        throw timeoutError;
      }

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
    let event: string | undefined;

    for (const line of lines) {
      if (line.startsWith("data:")) {
        data += `${line.slice(5).trim()}\n`;
      } else if (line.startsWith("id:")) {
        // Skip id for now as it's not used in our event handling
      } else if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      }
      // Ignore retry: field for simplicity
    }

    if (!data) return;

    // Remove trailing newline
    data = data.slice(0, -1);

    try {
      const parsedData = JSON.parse(data);

      if (event && this.handlers.onEvent) {
        this.handlers.onEvent(event as keyof TEventMap, parsedData);
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
      this.connect().catch((error) => {
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

/*
Usage Example:

import SSEClient from './sse-client';

// Define event map with type safety
interface EventMap {
  conversation_start: {
    conversation_id: number;
  };
  message_chunk: {
    message_id: number;
    content: string;
    conversation_id: number;
  };
  tool_call: {
    message_id: number;
    content: {
      tool_call_id: number;
      tool_name: string;
      tool_result: string;
    };
    conversation_id: number;
  };
  tool_call_result: {
    message_id: number;
    content: {
      tool_call_id: number;
      tool_name: string;
    };
    conversation_id: number;
  };
  reasoning: {
    message_id: number;
    content: string;
    conversation_id: number;
  };
  done: {
    message_id: number;
    conversation_id: number;
  };
}

// Create client with type-safe event map
const client = new SSEClient<EventMap>({
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
  onEvent: (eventType, data) => {
    // eventType and data are fully typed based on EventMap
    switch (eventType) {
      case 'conversation_start':
        // data is automatically typed as { conversation_id: number }
        console.log(`Conversation started: ${data.conversation_id}`);
        break;
        
      case 'message_chunk':
        // data is automatically typed as { message_id: number; content: string; conversation_id: number }
        console.log(`Message chunk: ${data.content}`);
        appendToMessage(data.message_id, data.content);
        break;
        
      case 'tool_call':
        // data is automatically typed with correct tool_call structure
        console.log(`Tool call: ${data.content.tool_name}`);
        showToolExecution(data.content.tool_name, data.content.tool_call_id);
        break;
        
      case 'tool_call_result':
        console.log(`Tool result: ${data.content.tool_call_id}`);
        updateToolResult(data.content.tool_call_id);
        break;
        
      case 'reasoning':
        console.log(`Reasoning: ${data.content}`);
        showReasoning(data.message_id, data.content);
        break;
        
      case 'done':
        console.log(`Message ${data.message_id} completed`);
        markMessageComplete(data.message_id);
        break;
    }
  },
  onOpen: () => console.log('SSE connection established'),
  onError: (error) => console.error('SSE connection error:', error),
  onClose: () => console.log('SSE connection closed'),
  onReconnect: (attempt) => console.log(`Reconnecting (attempt ${attempt})`),
});

// Helper functions for UI updates
function appendToMessage(messageId: number, content: string) {
  const messageElement = document.getElementById(`message-${messageId}`);
  if (messageElement) {
    messageElement.textContent += content;
  }
}

function showToolExecution(toolName: string, toolCallId: number) {
  console.log(`Executing tool: ${toolName} (ID: ${toolCallId})`);
}

function updateToolResult(toolCallId: number) {
  console.log(`Tool ${toolCallId} completed`);
}

function showReasoning(messageId: number, reasoning: string) {
  console.log(`Reasoning for message ${messageId}: ${reasoning}`);
}

function markMessageComplete(messageId: number) {
  console.log(`Message ${messageId} is complete`);
}

// Connect to stream
await client.connect();

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
